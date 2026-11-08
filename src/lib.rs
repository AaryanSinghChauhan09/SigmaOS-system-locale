// SPDX-License-Identifier: Apache-2.0
//! SigmaOS-system-locale — SigmaOS system-locale component inspired by Linux Mint / Omarchy / Arch Linux.
//!
//! Line-based `key = value` / `key: value` parser with comment support; deterministic BTreeMap output.
//! Principles: single responsibility, fail-fast, defensive programming,
//! component isolation, stable API, deterministic tests.

#![forbid(unsafe_code)]

use std::fmt;
use std::collections::BTreeMap;

/// Errors for `ParseError` operations. Fail-fast: invalid input is rejected.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParseError {
    /// Line has content but no '=' or ':' separator
    MissingSeparator(String),
    /// Key portion is empty
    EmptyKey,
    /// Key appears more than once
    DuplicateKey(String),
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MissingSeparator(x) => write!(f, "line has content but no '=' or ':' separator: {x}"),
            Self::EmptyKey => write!(f, "key portion is empty"),
            Self::DuplicateKey(x) => write!(f, "key appears more than once: {x}"),
        }
    }
}

impl std::error::Error for ParseError {}

/// Parse `key = value` or `key: value` lines into a sorted map.
/// Blank lines and `#` comments are ignored; keys are trimmed.
pub fn parse(input: &str) -> Result<BTreeMap<String, String>, ParseError> {
    let mut map = BTreeMap::new();
    for (lineno, raw) in input.lines().enumerate() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') { continue; }
        let pos = line.find(|c| c == '=' || c == ':')
            .ok_or_else(|| ParseError::MissingSeparator(format!("line {}", lineno + 1)))?;
        let key = line[..pos].trim();
        if key.is_empty() { return Err(ParseError::EmptyKey); }
        if map.contains_key(key) { return Err(ParseError::DuplicateKey(key.to_string())); }
        map.insert(key.to_string(), line[pos + 1..].trim().to_string());
    }
    Ok(map)
}

/// Serialize a map back to `key = value` lines (round-trip stable).
pub fn serialize(map: &BTreeMap<String, String>) -> String {
    map.iter().map(|(k, v)| format!("{k} = {v}")).collect::<Vec<_>>().join("\n") + "\n"
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_mixed_separators_and_comments() {
        let m = parse("# comment\nfoo = bar\nbaz: qux\n\n").unwrap();
        assert_eq!(m.get("foo").unwrap(), "bar");
        assert_eq!(m.get("baz").unwrap(), "qux");
        assert_eq!(m.len(), 2);
    }

    #[test]
    fn round_trip() {
        let m = parse("a = 1\nb = 2\n").unwrap();
        let s = serialize(&m);
        assert_eq!(parse(&s).unwrap(), m);
    }

    #[test]
    fn missing_separator_fails() {
        assert!(matches!(parse("just words"), Err(ParseError::MissingSeparator(_))));
    }

    #[test]
    fn duplicate_key_fails() {
        assert!(matches!(parse("a = 1\na = 2\n"), Err(ParseError::DuplicateKey(_))));
    }

}

/// Backwards-compatible component handle (kept for existing callers/tests).
#[derive(Debug, Default)]
pub struct Component {
    name: &'static str,
}

impl Component {
    /// Create the component handle.
    pub fn new() -> Self {
        Self { name: "SigmaOS Component" }
    }
}
