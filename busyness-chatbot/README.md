# Busyness Chatbot - OCR & GitHub Sync

A web application built with Python FastHTML and Google GenAI for extracting text from images and PDFs using OCR (Optical Character Recognition) with GitHub integration for content synchronization.

## Features

- Upload images (JPG, JPEG, PNG, GIF, BMP) or PDF files
- Extract text using Google's Gemini AI model
- **GitHub Integration** - Sync extracted content to your GitHub repository
- **Real-time Webhooks** - Receive notifications when repository changes
- Clean, responsive web interface with GitHub status indicators
- Docker support for easy deployment

## Prerequisites

- Python 3.11+
- Docker (optional)
- GitHub account with a repository
- GitHub Personal Access Token

## GitHub Setup

1. **Create a GitHub Personal Access Token:**
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate a new token with `repo` permissions
   - Copy the token

2. **Set Environment Variables:**
   ```bash
   # Required
   export GITHUB_TOKEN=your_github_token_here
   export GITHUB_REPO_OWNER=your_github_username
   
   # Optional (defaults to 'busyness-chatbot')
   export GITHUB_REPO_NAME=your_repo_name
   ```

3. **Create a `.env` file** (recommended):
   ```bash
   GITHUB_TOKEN=your_github_token_here
   GITHUB_REPO_OWNER=your_github_username
   GITHUB_REPO_NAME=busyness-chatbot
   ```

## Installation

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure GitHub integration (see GitHub Setup above)

3. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

### Docker Deployment

1. Build the Docker image:
```bash
docker build -t ocr-app .
```

2. Run the container:
```bash
docker run -p 5000:5000 ocr-app
```

The application will be available at `http://localhost:5000`

## Usage

1. Open your web browser and navigate to `http://localhost:5000`
2. Check the GitHub status indicator to ensure your repository is connected
3. Click "Choose File" and select an image or PDF file
4. Check "Sync to GitHub repository" if you want to save the extracted text to your repo
5. Click "Extract Text & Sync" to process the file
6. View the extracted text and GitHub sync status in the results section

### GitHub Integration Features

- **Automatic Sync**: Extracted text is automatically saved to your GitHub repository
- **File Organization**: Content is organized in an `extracted_content/` folder with timestamps
- **Real-time Status**: See your GitHub connection status and repository information
- **Webhook Support**: Set up webhooks for real-time notifications
- **Configuration Page**: Easy setup and configuration at `/github-config`

## API Key

The application uses a pre-configured Google GenAI API key. For production use, consider using environment variables for security.

## File Support

- **Images**: JPG, JPEG, PNG, GIF, BMP
- **Documents**: PDF

## Technology Stack

- **Backend**: Python FastHTML
- **AI/OCR**: Google GenAI (Gemini 1.5 Flash)
- **GitHub Integration**: PyGithub
- **Image Processing**: Pillow (PIL)
- **PDF Processing**: PyMuPDF
- **Environment Management**: python-dotenv
- **Containerization**: Docker with Debian base

## API Endpoints

- `GET /` - Main application interface
- `POST /upload` - Upload and process files with optional GitHub sync
- `GET /github-info` - Get GitHub repository information
- `POST /create-webhook` - Create GitHub webhook
- `GET /github-config` - GitHub configuration page
- `POST /webhook` - Handle GitHub webhook events

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_TOKEN` | GitHub Personal Access Token | Yes |
| `GITHUB_REPO_OWNER` | Your GitHub username | Yes |
| `GITHUB_REPO_NAME` | Repository name | No (defaults to 'busyness-chatbot') |
| `WEBHOOK_SECRET` | Webhook secret for security | No |

