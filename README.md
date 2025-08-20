# Narrative Hero

Narrative Hero is a web application for recording, transcribing, and managing voice notes. It provides a simple and intuitive interface to capture your thoughts and ideas, automatically transcribes them using AI, and generates a concise title for each note.

## Features

*   **Voice Recording:** Easily record voice notes directly in your browser.
*   **Automatic Transcription:** Uses Google's Gemini 1.5 Flash model to accurately transcribe your recordings.
*   **AI-Powered Titling:** Automatically generates a short, descriptive title for each note.
*   **Note Management:** View, play back, and delete your voice notes.
*   **Copy Transcription:** Quickly copy the full transcription to your clipboard.
*   **Metadata:** Option to include the date and your location in the note's metadata.

## Tech Stack

*   **Backend:**
    *   [FastAPI](https://fastapi.tiangolo.com/): A modern, fast (high-performance) web framework for building APIs with Python.
    *   [LangChain](https://www.langchain.com/): A framework for developing applications powered by language models.
    *   [Google Generative AI](https://ai.google.dev/): Used for the transcription and title generation models.
*   **Frontend:**
    *   [SvelteKit](https://kit.svelte.dev/): A framework for building web applications of all sizes, with a beautiful development experience and flexible filesystem-based routing.
*   **Deployment:**
    *   [Docker](https://www.docker.com/): The application is containerized for easy setup and deployment.
    *   [Docker Compose](https://docs.docker.com/compose/): Used to define and run the multi-container application.

## Getting Started

To get the project up and running, you'll need to have [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/) installed.

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/narrative-hero.git
    cd narrative-hero
    ```

2.  **Set up your environment variables:**

    The backend service requires a Google API key to use the transcription and title generation features. Create a `.env` file in the `backend` directory:

    ```
    backend/.env
    ```

    Add your Google API key to this file:

    ```
    GOOGLE_API_KEY="your-google-api-key"
    ```

3.  **Build and run the application:**

    ```bash
    docker-compose up --build
    ```

4.  **Access the application:**

    Once the containers are running, you can access the Narrative Hero web interface in your browser at:

    [http://localhost](http://localhost)

    The backend API will be available at `http://localhost:8000`.

## Project Structure

*   `backend/`: Contains the FastAPI application for the backend API.
*   `frontend/`: Contains the SvelteKit application for the frontend user interface.
*   `voice_notes/`: This directory is created automatically and stores the recorded audio files, transcriptions, and titles.
*   `compose.yaml`: The Docker Compose file for defining and running the application services.