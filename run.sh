#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: ./run.sh [cooja|dongle|help]"
    exit 1
fi

if [ "$1" != "cooja" ] && [ "$1" != "dongle" ] && [ "$1" != "help" ]; then
    echo "Invalid argument."
    echo "Usage: ./run.sh [cooja|dongle|help]"
    exit 1
fi

if [ "$1" == "help" ]; then
    echo "Usage: ./run.sh [cooja|dongle]"
    echo "  cooja: Starts the Cooja simulator and the border router."
    echo "  dongle: Starts the border router with the dongle."
    exit 0
fi

# venv name
VENV_NAME=leathersense

# venv directory
VENV_DIR=$(dirname $(realpath $0))

# If the virtual environment does not exist, create it
if [ ! -d "/$VENV_DIR/$VENV_NAME" ]; then
    echo "Creating virtual environment..."
    virtualenv /$VENV_DIR/$VENV_NAME
    source /$VENV_DIR/$VENV_NAME/bin/activate
    # Install the required packages
    pip install -r requirements.txt
else
    # Activate the virtual environment
    source /$VENV_DIR/$VENV_NAME/bin/activate
    pip install -q -r requirements.txt
fi

# List of scripts to run
gnome-terminal --geometry=50x10+0+0 --title="CoAP Registration Server" -- bash -c "source /$VENV_DIR/$VENV_NAME/bin/activate && python /$VENV_DIR/CoAP-RegistrationServer/main.py; exec bash"
gnome-terminal --geometry=50x10+0+0 --title="MQTT Client" -- bash -c "source /$VENV_DIR/$VENV_NAME/bin/activate && python /$VENV_DIR/MQTT-Client/main.py; exec bash"
gnome-terminal --geometry=100x40+0+0 --title="Remote Control Application" -- bash -c "source /$VENV_DIR/$VENV_NAME/bin/activate && python /$VENV_DIR/RemoteControlApplication/main.py; exec bash"

echo "All scripts started."

if [ "$1" == "cooja" ]; then
    # Starts cooja
    chmod +x /$VENV_DIR/cooja/cooja-start.sh
    gnome-terminal -- bash -c "source /$VENV_DIR/$VENV_NAME/bin/activate && /$VENV_DIR/cooja/cooja-start.sh; exec bash"

    # Pause the script
    read -p "Press any key to activate the border router..."

    # Activate border router
    gnome-terminal --geometry=50x10+0+0 --title="Border Router" -- bash -c "source /$VENV_DIR/$VENV_NAME/bin/activate && cd /$VENV_DIR/rpl-border-router && make TARGET=cooja connect-router-cooja; exec bash"
elif [ "$1" == "dongle" ]; then
    # Starts the dongle
    gnome-terminal --geometry=50x10+0+0 --title="Border Router" -- bash -c "source /$VENV_DIR/$VENV_NAME/bin/activate && cd /$VENV_DIR/rpl-border-router && make PORT=/dev/ttyACM0 connect-router; exec bash"
else
    echo "Invalid argument."
    echo "Usage: ./run.sh [cooja|dongle|help]"
    deactivate
    exit 1
fi

# Deactivate the virtual environment
deactivate

exit 0
