# Ginseng Pai Sho

The goal of this personal project was to create Giseng Pai Sho, a game from [this](https://skudpaisho.com/) website, which hosts many Pai Sho variations. Pai Sho is a game from Avatar: The Last Airbender.

## Prerequisites

This project requires **Python 3.12.10**. 
Please ensure you have this specific version installed before proceeding. You can check your version by running `python --version` in your terminal.

## Setup and Installation

Follow these steps to download the project and install its dependencies.

### 1. Clone the Repository
Clone this project to your local machine and navigate into the project directory:
```bash
git clone https://github.com/MihirLikesToCode/GinsengPaiSho.git
cd GinsengPaiSho
```

### 2. Create a Virtual Environment
Create a fresh, isolated virtual environment using Python 3.12.10:

*   **macOS / Linux:**
    ```bash
    python3.12 -m venv venv
    ```
*   **Windows:**
    ```bash
    py -3.12 -m venv venv
    ```

### 3. Activate the Virtual Environment
Activate the environment to ensure dependencies are installed locally:

*   **macOS / Linux:**
    ```bash
    source venv/bin/activate
    ```
*   **Windows (Command Prompt):**
    ```cmd
    venv\Scripts\activate.bat
    ```
*   **Windows (PowerShell):**
    ```powershell
    .\venv\Scripts\Activate.ps1
    ```
*Once activated, your terminal prompt will display `(venv)`.*

### 4. Install Dependencies
Install all required packages listed in the `requirements.txt` file:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Running the Project

With your virtual environment activated, run the main project script:
```bash
python Game.py
```


## Deactivation
When you are done working on the project, you can exit the virtual environment by running:
```bash
deactivate
```
