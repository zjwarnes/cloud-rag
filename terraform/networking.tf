# VPC Network
resource "google_compute_network" "rag_network" {
  name                    = "${var.service_name_prefix}-network"
  auto_create_subnetworks = true
}

# Firewall rule (allow egress to external APIs)
resource "google_compute_firewall" "allow_egress" {
  name      = "${var.service_name_prefix}-allow-egress"
  network   = google_compute_network.rag_network.name
  direction = "EGRESS"

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  destination_ranges = ["0.0.0.0/0"]
}
