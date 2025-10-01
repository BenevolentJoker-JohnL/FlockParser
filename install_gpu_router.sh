#!/bin/bash
# GPU Router Daemon Installation Script
# Installs the standalone GPU router daemon as a systemd service

set -e  # Exit on error

echo "="
echo "🚀 GPU Router Daemon Installation"
echo "="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Please run this script as a regular user (not root)"
    echo "   The script will use sudo when needed"
    exit 1
fi

# Configuration
INSTALL_DIR="/opt/gpu-router"
SERVICE_FILE="gpu-router.service"
DAEMON_SCRIPT="gpu_router_daemon.py"
CONFIG_FILE="gpu_router_config.yaml"
LOG_DIR="/var/log/gpu-router"
CURRENT_USER=$(whoami)

echo ""
echo "📋 Installation Configuration:"
echo "   Install directory: $INSTALL_DIR"
echo "   Service file: /etc/systemd/system/$SERVICE_FILE"
echo "   Log directory: $LOG_DIR"
echo "   Running as user: $CURRENT_USER"
echo ""

# Check required files exist
echo "🔍 Checking required files..."
required_files=("$DAEMON_SCRIPT" "intelligent_gpu_router.py" "vram_monitor.py" "gpu_controller.py")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Error: Required file not found: $file"
        echo "   Please run this script from the FlockParser directory"
        exit 1
    fi
    echo "   ✅ Found $file"
done

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip3 install pyyaml requests --user || {
    echo "⚠️  Warning: Could not install Python dependencies"
    echo "   You may need to install them manually:"
    echo "   pip3 install pyyaml requests"
}

# Create installation directory
echo ""
echo "📁 Creating installation directory..."
sudo mkdir -p "$INSTALL_DIR"
echo "   ✅ Created $INSTALL_DIR"

# Copy files
echo ""
echo "📋 Copying files..."
sudo cp "$DAEMON_SCRIPT" "$INSTALL_DIR/"
sudo cp "intelligent_gpu_router.py" "$INSTALL_DIR/"
sudo cp "vram_monitor.py" "$INSTALL_DIR/"
sudo cp "gpu_controller.py" "$INSTALL_DIR/"
sudo cp "$CONFIG_FILE" "$INSTALL_DIR/"
sudo chmod +x "$INSTALL_DIR/$DAEMON_SCRIPT"
echo "   ✅ Files copied to $INSTALL_DIR"

# Set ownership
sudo chown -R "$CURRENT_USER:$CURRENT_USER" "$INSTALL_DIR"

# Create log directory
echo ""
echo "📝 Creating log directory..."
sudo mkdir -p "$LOG_DIR"
sudo chown "$CURRENT_USER:$CURRENT_USER" "$LOG_DIR"
echo "   ✅ Created $LOG_DIR"

# Update service file with current user
echo ""
echo "🔧 Configuring systemd service..."
temp_service=$(mktemp)
sed "s/User=joker/User=$CURRENT_USER/g; s/Group=joker/Group=$CURRENT_USER/g; s|WorkingDirectory=/home/joker/FlockParser|WorkingDirectory=$INSTALL_DIR|g; s|/home/joker/FlockParser|$INSTALL_DIR|g" "$SERVICE_FILE" > "$temp_service"

# Install service file
sudo cp "$temp_service" "/etc/systemd/system/$SERVICE_FILE"
rm "$temp_service"
echo "   ✅ Service file installed"

# Reload systemd
echo ""
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload
echo "   ✅ Systemd reloaded"

# Prompt for configuration
echo ""
echo "="
echo "⚙️  CONFIGURATION"
echo "="
echo ""
echo "Before starting the service, please edit the configuration file:"
echo "   sudo nano $INSTALL_DIR/$CONFIG_FILE"
echo ""
echo "Update the following settings:"
echo "   - nodes: Add your Ollama node URLs"
echo "   - priority_models: Models to keep on GPU"
echo "   - check_interval: How often to check (seconds)"
echo ""
read -p "Press Enter when you've finished editing the configuration..."

# Enable and start service
echo ""
echo "🚀 Enabling and starting service..."
sudo systemctl enable "$SERVICE_FILE"
sudo systemctl start "$SERVICE_FILE"
echo "   ✅ Service enabled and started"

# Show status
echo ""
echo "="
echo "✅ INSTALLATION COMPLETE"
echo "="
echo ""
echo "Service Status:"
sudo systemctl status "$SERVICE_FILE" --no-pager || true
echo ""
echo "📋 Useful commands:"
echo "   View logs:        sudo journalctl -u $SERVICE_FILE -f"
echo "   Check status:     sudo systemctl status $SERVICE_FILE"
echo "   Stop service:     sudo systemctl stop $SERVICE_FILE"
echo "   Start service:    sudo systemctl start $SERVICE_FILE"
echo "   Restart service:  sudo systemctl restart $SERVICE_FILE"
echo "   Disable service:  sudo systemctl disable $SERVICE_FILE"
echo ""
echo "📝 Configuration file: $INSTALL_DIR/$CONFIG_FILE"
echo "📊 Log directory: $LOG_DIR"
echo ""
echo "🎉 GPU Router Daemon is now running!"