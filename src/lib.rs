//! SigmaOS-system-locale — System locale and language settings for SigmaOS
#![allow(dead_code)]

pub mod backup;
pub mod config;
pub mod error;
pub mod service;
pub mod system;

pub use backup::{BackupManager, Snapshot, SnapshotType};
pub use config::Config;
pub use error::{ComponentError, Result};
pub use service::Service;
pub use system::{ResourceStatus, SystemMonitor, SystemResource};

pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}
