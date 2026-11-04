use sigmaos_system_component::{SystemMonitor, SystemResource, ResourceStatus};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_system_monitor_new_aaa() {
        // Arrange
        let monitor = SystemMonitor::new();
        // Act & Assert
        assert!(monitor.check_health());
    }

    #[test]
    fn test_system_resource_critical_aaa() {
        // Arrange
        let mut monitor = SystemMonitor::new();
        let resource = SystemResource {
            name: "cpu".to_string(),
            usage: 99.0,
            status: ResourceStatus::Critical,
        };
        // Act
        monitor.add_resource(resource);
        // Assert
        assert!(!monitor.check_health());
    }

    #[test]
    fn test_system_resource_normal_aaa() {
        // Arrange
        let mut monitor = SystemMonitor::new();
        let resource = SystemResource {
            name: "mem".to_string(),
            usage: 50.0,
            status: ResourceStatus::Normal,
        };
        // Act
        monitor.add_resource(resource);
        // Assert
        assert!(monitor.check_health());
    }
}
