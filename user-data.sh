#!/bin/bash

# Update the system
yum update -y

# Install Python 3 and pip
yum install python3 python3-pip -y

# Install development tools (needed for some Python packages)
yum groupinstall "Development Tools" -y

# Upgrade pip
pip3 install --upgrade pip

# Install required Python packages
pip3 install flask flask-session redis boto3 gunicorn

# Install AWS CLI
pip3 install awscli

# Install Git (if you want to clone your repository)
yum install git -y

# Create a directory for the application
mkdir -p /home/ec2-user/bedrock-chatbot
cd /home/ec2-user/bedrock-chatbot

# Clone your repository (replace with your actual repository URL)
# git clone https://github.com/yourusername/bedrock-chatbot.git .

# Set correct permissions
chown -R ec2-user:ec2-user /home/ec2-user/bedrock-chatbot

# Create a simple startup script
cat << EOF > /home/ec2-user/start_chatbot.sh
#!/bin/bash
cd /home/ec2-user/bedrock-chatbot
gunicorn --bind 0.0.0.0:5000 wsgi:app -w1
EOF

chmod +x /home/ec2-user/start_chatbot.sh

# Set up a systemd service for the chatbot
cat << EOF > /etc/systemd/system/bedrock-chatbot.service
[Unit]
Description=Bedrock Chatbot
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/bedrock-chatbot
ExecStart=/home/ec2-user/start_chatbot.sh
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd, enable and start the service
systemctl daemon-reload
systemctl enable bedrock-chatbot.service
systemctl start bedrock-chatbot.service

# Print completion message
echo "Bedrock Chatbot setup complete!"