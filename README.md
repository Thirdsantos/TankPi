# TANK PI, Raspberry Pi Aquarium Monitoring Backend

A sophisticated IoT backend system built with FastAPI for real-time aquarium monitoring and control. This project transforms your Raspberry Pi into a smart aquarium management hub with live video streaming, sensor monitoring, and automated control capabilities.

**Part of the AquaCare Ecosystem** - This Raspberry Pi backend integrates seamlessly with the AquaCare platform for comprehensive aquarium management.

##  Features

###  **Live Video Streaming**
- **Real-time Camera Feed**: Live video streaming via WebSocket connections
- **Camera Control**: Remote camera on/off functionality through REST API and WebSocket
- **Optimized Performance**: Configurable resolution (320x240), FPS (15), and JPEG quality (30)
- **Multi-client Support**: Multiple clients can connect simultaneously to view the aquarium

###  **Sensor Monitoring**
- **Real-time Data**: Continuous sensor data collection every 3 seconds
- **Hourly Logging**: Automated hourly data logging for historical analysis
- **Multi-parameter Tracking**: Monitors pH, temperature, and turbidity levels
- **Cloud Integration**: Seamless data transmission to AquaCare monitoring services

###  **Smart Automation**
- **Background Scheduler**: Automated task management using APScheduler
- **Real-time Updates**: Continuous sensor data transmission to AquaCare
- **Scheduled Operations**: Automated hourly data logging and reporting

###  **Modern Web API**
- **FastAPI Framework**: High-performance, modern Python web framework
- **WebSocket Support**: Real-time bidirectional communication
- **RESTful Endpoints**: Clean API design for easy integration
- **Async Operations**: Non-blocking I/O for optimal performance

##  Getting Started

### Prerequisites
- Raspberry Pi (3 or 4 recommended)
- USB camera or Pi Camera module
- Python 3.8+
- Internet connection for AquaCare cloud data transmission
- AquaCare account and aquarium ID

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Thirdsantos/TankPi.git
   cd raspi_backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure AquaCare Connection**
   - Update the `aquarium` ID in `run.py` to match your AquaCare aquarium
   - Ensure your Raspberry Pi has internet access to reach AquaCare services

5. **Run the application**
   ```bash
   python run.py
   ```

The server will start on `http://localhost:8000`

##  API Endpoints

### Camera Control
- `POST /aquarium/{id}/camera_switch` - Toggle camera on/off
- `WebSocket /aquarium/{id}/camera/ws` - Live video stream
- `WebSocket /aquarium/{id}/camera/control` - Camera control interface

### Sensor Data
- **Real-time**: Data sent every 3 seconds to AquaCare cloud service
- **Hourly Logs**: Historical data logged every hour to AquaCare

## 🔗 AquaCare Integration

This Raspberry Pi backend is designed to work as a **local node** within the AquaCare ecosystem:

- **Local Processing**: Handles real-time video streaming and sensor data locally
- **Cloud Sync**: Automatically transmits data to AquaCare cloud services
- **Remote Access**: Access your aquarium from anywhere through the AquaCare platform
- **Multi-Aquarium Support**: Configure multiple aquarium IDs for different tanks
- **Data Analytics**: Leverage AquaCare's advanced analytics and reporting features

##  Future Roadmap

###  **Machine Learning Integration**
- **Water Quality Prediction**: ML models to predict optimal water conditions
- **Anomaly Detection**: AI-powered detection of unusual sensor readings
- **Predictive Maintenance**: Forecast equipment maintenance needs
- **Behavioral Analysis**: Analyze fish behavior patterns from video feeds

###  **Auto-Feeding System**
- **Smart Scheduling**: ML-optimized feeding schedules based on fish behavior
- **Portion Control**: Automated portion sizing based on fish population
- **Health Monitoring**: Adjust feeding based on water quality and fish health
- **Remote Control**: Mobile app integration for manual feeding override

###  **Enhanced User Experience**
- **Mobile App**: Cross-platform mobile application
- **Dashboard**: Real-time monitoring dashboard with historical data
- **Notifications**: Smart alerts for critical water quality issues
- **Voice Control**: Integration with smart home assistants

##  Technology Stack

- **Backend**: FastAPI, Uvicorn
- **Video Processing**: OpenCV
- **Scheduling**: APScheduler
- **Data Transmission**: Requests, WebSockets
- **Data Validation**: Pydantic
- **Async Support**: asyncio
- **Cloud Integration**: AquaCare API services

##  Project Structure

```
raspi_backend/
├── app/
│   ├── routes/
│   │   ├── video.py          # Video streaming endpoints
│   │   └── sensors.py        # Sensor data handling & AquaCare integration
│   ├── services/
│   │   └── camera.py         # Camera service utilities
│   └── main.py               # FastAPI application with AquaCare scheduler
├── requirements.txt           # Python dependencies
├── run.py                    # Application entry point & AquaCare config
└── README.md                 # This file
```


- Built with FastAPI for high-performance web APIs
- Powered by Raspberry Pi for IoT capabilities
- OpenCV for computer vision and video processing
- APScheduler for automated task management
- **Integrated with AquaCare cloud platform for comprehensive aquarium management**

