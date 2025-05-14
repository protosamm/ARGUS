
# **ARGUS - Autonomous Realtime Guardian and Security System**

The ARGUS is a real time threat detection system which utilizes deep learning algorithm and computer vision technology to detect individuals who can be a potential threat, through live camera feed.


# Project Setup and Run Guide

This project uses both Node.js and Python. Follow the steps below to get it running on your machine.

## 📦 Prerequisites

Make sure the following are installed:

- [Node.js](https://nodejs.org/) (v14+ recommended)
- [Python 3.x](https://www.python.org/) (use the version which is compatible with mediapipe)
- `pip` (comes with Python)

### 1. Clone the repository

```bash
git clone https://github.com/protosamm/ARGUS.git
```

### 2. Install Node.js dependencies
```bash
npm install
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

## 🚀 Running the Project

### 1. Start the Node.js server
```bash
node server.js
```
This will start your backend or socket server.

### 2. Run the Python script
Open a second terminal, navigate to the project directory, and run:
```bash
python argus.py
```
Now both scripts should be running and communicating as expected.
## Screenshots
Already generated alerts can be opened.
![Picture5](https://github.com/user-attachments/assets/3a7de123-1158-48d9-a760-e8f7860e0ed7)

New alerts will pop up on the screen automatically
![Picture4](https://github.com/user-attachments/assets/ef62d832-c260-4e02-8717-40305a288c07)
