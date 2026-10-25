"""Locale manager for SigmaOS-system-locale (inspired by mintlocale).

Pure plan/validate layer over locale.gen-style data and an env dict:
listing, availability, current state, and an idempotent enable plan.
Setting a locale produces a plan (edit locale.gen, run locale-gen, update
environment) -- execution is a thin opt-in layer, never run by self_test.
"""
import argparse, os, re, sys

ENGINE = {
    "name": "sigma-locale",
    "summary": "List, validate and plan system locale changes",
    "language": "python",
    "verbs": ["list", "set", "available", "current"],
    "principles": ["Plan Before Apply", "Fail-Fast", "Idempotence",
                   "KISS", "Deterministic Testing"],
}

cli_doc = """\
$ sigma-locale current --env env.json
$ sigma-locale list --gen locale.gen
$ sigma-locale available --catalog /usr/share/i18n/SUPPORTED
$ sigma-locale set --gen locale.gen --lang en_GB.UTF-8 --layout us \\
      --plan plan.sh
"""

LOCALE_RE = re.compile(r"^[a-z]{2,3}(_[A-Z]{2})?(\.[\w-]+)?(@[\w+.-]+)?$")
LAYOUT_RE = re.compile(r"^[\w+-]{1,16}$")


class LocaleError(Exception):
    pass


def validate_locale(tag):
    """Pure: a locale tag must look like ll, ll_CC or ll_CC@variant."""
    if not isinstance(tag, str) or not LOCALE_RE.match(tag):
        raise LocaleError(f"invalid locale tag: {tag!r}")
    return tag


def validate_layout(name):
    """Pure: keyboard layout codes are short and simple ('us', 'de', 'us+intl')."""
    if not isinstance(name, str) or not LAYOUT_RE.match(name):
        raise LocaleError(f"invalid keyboard layout: {name!r}")
    return name


def parse_locale_gen(text):
    """Parse locale.gen content -> [{locale, encodings, enabled}]."""
    entries = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        enabled = True
        if line.startswith("#"):
            enabled = False
            line = line.lstrip("#").strip()
        parts = line.split()
        if not parts:
            continue
        locale = parts[0]
        encodings = parts[1:] or ["UTF-8"]
        if not LOCALE_RE.match(locale):
            raise LocaleError(f"line {lineno}: bad locale {locale!r}")
        entries.append({"locale": locale, "encodings": encodings,
                        "enabled": enabled})
    return entries


def parse_catalog(text):
    """Parse a SUPPORTED-style catalog -> sorted locale list."""
    locales = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        locale = line.split()[0]
        if LOCALE_RE.match(locale):
            locales.append(locale)
    return sorted(set(locales))


def plan_enable(text, locale, layout=None):
    """Pure: plan to enable `locale` in locale.gen (idempotent)."""
    validate_locale(locale)
    if layout is not None:
        validate_layout(layout)
    entries = parse_locale_gen(text)
    known = {e["locale"] for e in entries}
    if locale not in known:
        raise LocaleError(f"locale not present in file: {locale} "
                          "(add it or pick from `available`)")
    if any(e["locale"] == locale and e["enabled"] for e in entries):
        return {"changed": False, "edits": [], "commands": [],
                "env": {"LANG": locale, "LC_ALL": locale}}
    edits = []
    for raw in text.splitlines():
        m = re.match(r"^#\s*(" + re.escape(locale) + r")(\s.*)?$", raw.strip())
        if m:
            edits.append({"op": "uncomment", "line": locale})
    if not edits:
        edits = [{"op": "append", "line": locale + " UTF-8"}]
    commands = ["locale-gen"]
    if layout is not None:
        commands.append(f"localectl set-keymap {layout}")
    return {"changed": True, "edits": edits, "commands": commands,
            "env": {"LANG": locale, "LC_ALL": locale}}


def current_state(env):
    """Pure: summarize locale state from an injected env mapping."""
    lang = env.get("LANG")
    if lang:
        validate_locale(_base_tag(lang))
    languages = [l for l in (env.get("LANGUAGE") or "").split(":") if l]
    for l in languages:
        validate_locale(_base_tag(l))
    return {"lang": lang,
            "messages": languages,
            "lc_all": env.get("LC_ALL"),
            "keymap": env.get("KEYMAP")}


def _base_tag(tag):
    """ll_CC.UTF-8@euro -> ll_CC (validation helper)."""
    return tag.split(".")[0].split("@")[0]


def render_locale_gen(entries):
    """Pure inverse of parse_locale_gen (deterministic)."""
    lines = []
    for e in entries:
        prefix = "" if e["enabled"] else "# "
        lines.append(prefix + " ".join([e["locale"]] + e["encodings"]))
    return "\n".join(lines) + ("\n" if lines else "")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=ENGINE["name"], description=ENGINE["summary"])
    sub = p.add_subparsers(dest="cmd", required=True)
    cu = sub.add_parser("current", help="show current locale state")
    cu.add_argument("--env", required=True, help="JSON {VAR: value} env file")
    ls = sub.add_parser("list", help="list entries in a locale.gen file")
    ls.add_argument("--gen", required=True)
    av = sub.add_parser("available", help="list locales from a catalog")
    av.add_argument("--catalog", required=True)
    st = sub.add_parser("set", help="plan enabling a locale (dry-run)")
    st.add_argument("--gen", required=True)
    st.add_argument("--lang", required=True)
    st.add_argument("--layout", default=None)
    st.add_argument("--execute", action="store_true",
                    help="write locale.gen and print the commands")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "current":
            import json
            with open(args.env) as fh:
                env = json.load(fh)
            state = current_state(env)
            for k in ("lang", "messages", "lc_all", "keymap"):
                print(f"{k}: {state[k]}")
        elif args.cmd == "list":
            with open(args.gen) as fh:
                entries = parse_locale_gen(fh.read())
            for e in entries:
                mark = "*" if e["enabled"] else " "
                print(f"{mark} {e['locale']:24} {' '.join(e['encodings'])}")
        elif args.cmd == "available":
            with open(args.catalog) as fh:
                for loc in parse_catalog(fh.read()):
                    print(loc)
        elif args.cmd == "set":
            with open(args.gen) as fh:
                text = fh.read()
            plan = plan_enable(text, args.lang, args.layout)
            import json
            print(json.dumps(plan, indent=2))
            if args.execute and plan["changed"]:
                out = []
                for raw in text.splitlines():
                    m = re.match(r"^#\s*" + re.escape(args.lang) + r"(\s.*)?$",
                                 raw.strip())
                    if m:
                        out.append(args.lang + (m.group(1) or " UTF-8"))
                    else:
                        out.append(raw)
                with open(args.gen, "w") as fh:
                    fh.write("\n".join(out) + "\n")
                print("locale.gen updated; run: " + "; ".join(plan["commands"]))
            elif not plan["changed"]:
                print("already enabled")
        return 0
    except (LocaleError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def self_test() -> None:
    # validation
    for good in ("en", "en_US", "en_US.UTF-8", "zh_CN@pinyin", "sr_RS@latin",
                 "de_DE.UTF-8@euro"):
        validate_locale(_base_tag(good))  # base tag must validate
    for bad in ("EN_us", "en-US", "french", "", "en_US!", "x" * 40):
        try:
            validate_locale(bad)
        except LocaleError:
            pass
        else:
            raise AssertionError(f"locale not rejected: {bad!r}")
    validate_layout("us")
    validate_layout("de+nodeadkeys")
    for bad in ("", "U S", "x" * 20):
        try:
            validate_layout(bad)
        except LocaleError:
            pass
        else:
            raise AssertionError(f"layout not rejected: {bad!r}")

    gen = """\
# en_US.UTF-8 UTF-8
en_GB.UTF-8 UTF-8
# de_DE.UTF-8 UTF-8
fr_FR.UTF-8 UTF-8
"""
    entries = parse_locale_gen(gen)
    assert [e["locale"] for e in entries] == \
        ["en_US.UTF-8", "en_GB.UTF-8", "de_DE.UTF-8", "fr_FR.UTF-8"]
    assert [e["enabled"] for e in entries] == [False, True, False, True]

    # enable an already-enabled locale -> no-op (idempotent)
    plan = plan_enable(gen, "en_GB.UTF-8")
    assert plan["changed"] is False and plan["edits"] == []
    assert plan["env"]["LANG"] == "en_GB.UTF-8"

    # enable a commented locale -> uncomment + locale-gen
    plan = plan_enable(gen, "de_DE.UTF-8", layout="de")
    assert plan["changed"] is True
    assert plan["edits"] == [{"op": "uncomment", "line": "de_DE.UTF-8"}]
    assert plan["commands"] == ["locale-gen", "localectl set-keymap de"]

    try:
        plan_enable(gen, "ja_JP.UTF-8")  # not present in file
    except LocaleError as e:
        assert "not present" in str(e)
    else:
        raise AssertionError("unknown locale not caught")
    try:
        plan_enable(gen, "bad locale")
    except LocaleError:
        pass
    else:
        raise AssertionError("invalid tag not caught")

    # rendering round-trip
    text = render_locale_gen(entries)
    assert parse_locale_gen(text) == entries
    assert "# en_US.UTF-8 UTF-8" in text

    # catalog
    catalog = "en_US.UTF-8 UTF-8\nen_US ISO-8859-1\n# comment\nde_DE.UTF-8 UTF-8\n"
    assert parse_catalog(catalog) == ["de_DE.UTF-8", "en_US", "en_US.UTF-8"]
    assert parse_catalog("") == []

    # current state
    state = current_state({"LANG": "en_GB.UTF-8",
                           "LANGUAGE": "en_GB:en_US:en",
                           "LC_ALL": "en_GB.UTF-8", "KEYMAP": "gb"})
    assert state["lang"] == "en_GB.UTF-8"
    assert state["messages"] == ["en_GB", "en_US", "en"]
    assert state["keymap"] == "gb"
    empty = current_state({})
    assert empty == {"lang": None, "messages": [], "lc_all": None, "keymap": None}
    try:
        current_state({"LANG": "not a locale"})
    except LocaleError:
        pass
    else:
        raise AssertionError("bad LANG not caught")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
