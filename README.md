# Narrative Hero

Narrative Hero is a web application that allows users to record voice notes and generate narratives from them using Google's Gemini AI.

## Features

*   **Voice Note Recording:** Easily record and save voice notes directly in the browser.
*   **File Upload:** Upload existing audio files for processing.
*   **Date and Location Tagging:** Optionally tag notes with the current date and your geographical location.
*   **Automatic Transcription and Titling:** Each note is automatically transcribed and given a descriptive title.
*   **Narrative Generation:** Uses LangChain and Google's Gemini AI to generate stories and narratives based on the recorded voice notes.
*   **Web-based Interface:** A user-friendly interface built with SvelteKit for managing notes and generated content.

## Tech Stack

*   **Frontend:** SvelteKit, TypeScript
*   **Backend:** Python, FastAPI, LangChain, Google Gemini
*   **Containerization:** Docker, Docker Compose

## Prerequisites

*   Docker and Docker Compose (for containerized deployment)
*   Node.js and npm (for local frontend development)
*   Python 3.8+ and pip (for local backend development)
*   A Google AI API Key

## Running the Project

### Production (using Docker)

This is the recommended way to run the project.

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd narrative-hero
    ```

2.  **Create a `.env` file:**
    Create a `.env` file in the `backend` directory and add your Google AI API key:
    ```
    GOOGLE_API_KEY="your-api-key"
    ```

3.  **Build and run the application with Docker Compose:**
    ```bash
    docker-compose up --build
    ```

4.  **Access the application:**
    The frontend will be available at `http://localhost`.

### Local Development

For development, you can run the frontend and backend services separately.

#### Backend

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Create a `.env` file:**
    Create a `.env` file in the `backend` directory and add your Google AI API key:
    ```
    GOOGLE_API_KEY="your-api-key"
    ```

4.  **Run the backend development server:**
    ```bash
    ./dev.sh
    ```
    The backend API will be available at `http://localhost:8000`.

#### Frontend

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Run the frontend development server:**
    ```bash
    npm run dev
    ```
    The frontend will be available at `http://localhost:5173`.

## Project Structure

*   `frontend/`: Contains the SvelteKit frontend application. The UI is built with a component-based architecture, including components for file uploads, note display, and recording controls.
*   `backend/`: Contains the Python FastAPI backend, including the logic for audio processing and narrative generation.
*   `voice_notes/`: Directory where the recorded voice notes are stored.
*   `narratives/`: Directory where the generated narratives are stored.
*   `compose.yaml`: Defines the services, networks, and volumes for Docker Compose.
