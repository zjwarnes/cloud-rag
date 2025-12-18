# Cloud Logging
resource "google_logging_project_sink" "rag_api_logs" {
  name                   = "${var.service_name_prefix}-logs"
  destination            = "logging.googleapis.com/projects/${var.gcp_project_id}/logs/rag-api"
  filter                 = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${var.service_name_prefix}\""
  unique_writer_identity = true
}

# Cloud Monitoring - Alert on high error rate
resource "google_monitoring_alert_policy" "rag_api_errors" {
  display_name = "${var.service_name_prefix} - High Error Rate"
  combiner     = "OR"

  conditions {
    display_name = "Error Rate > 5%"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${var.service_name_prefix}\" AND metric.labels.response_code_class=\"5xx\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05
    }
  }

  notification_channels = [] # Add your notification channels here
}

# Cloud Monitoring - Alert on high latency
resource "google_monitoring_alert_policy" "rag_api_latency" {
  display_name = "${var.service_name_prefix} - High Latency"
  combiner     = "OR"

  conditions {
    display_name = "p99 Latency > 10s"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_latencies\" resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${var.service_name_prefix}\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 10000 # milliseconds
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_PERCENTILE_99"
      }
    }
  }

  notification_channels = []
}
