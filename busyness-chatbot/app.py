from fasthtml import *
import google.generativeai as genai
import os
import tempfile
from PIL import Image
import fitz  # PyMuPDF for PDF processing
import io
import base64
from github import Github
import requests
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Google GenAI
genai.configure(api_key="AIzaSyCft3MggADURL-aGknxHDLaemxaFvqMtg4")

# Initialize the model
model = genai.GenerativeModel('gemini-1.5-flash')

# GitHub Configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_REPO_OWNER = os.getenv('GITHUB_REPO_OWNER', '')
GITHUB_REPO_NAME = os.getenv('GITHUB_REPO_NAME', 'busyness-chatbot')

# Initialize GitHub client
github_client = None
if GITHUB_TOKEN:
    github_client = Github(GITHUB_TOKEN)

# Global storage for extracted content
extracted_content_store = {}

def extract_text_from_image(image_data):
    """Extract text from image using Google GenAI"""
    try:
        # Convert image data to PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to base64 for GenAI
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Create the prompt for OCR
        prompt = "Extract all text from this image. Return only the text content, no additional formatting or explanations."
        
        # Generate content with the image
        response = model.generate_content([prompt, {"mime_type": "image/png", "data": img_base64}])
        
        return response.text
    except Exception as e:
        return f"Error processing image: {str(e)}"

def extract_text_from_pdf(pdf_data):
    """Extract text from PDF using PyMuPDF and then process images with GenAI"""
    try:
        # Open PDF with PyMuPDF
        pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
        extracted_text = ""
        
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            
            # Try to extract text directly first
            page_text = page.get_text()
            if page_text.strip():
                extracted_text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
            else:
                # If no text, try OCR on the page image
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                ocr_text = extract_text_from_image(img_data)
                extracted_text += f"\n--- Page {page_num + 1} (OCR) ---\n{ocr_text}\n"
        
        pdf_document.close()
        return extracted_text
    except Exception as e:
        return f"Error processing PDF: {str(e)}"

def sync_to_github(content, filename, file_type="text"):
    """Sync extracted content to GitHub repository"""
    if not github_client or not GITHUB_REPO_OWNER:
        return {"success": False, "message": "GitHub not configured. Please set GITHUB_TOKEN and GITHUB_REPO_OWNER environment variables."}
    
    try:
        # Get the repository
        repo = github_client.get_repo(f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
        
        # Create a unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
        github_filename = f"extracted_content/{safe_filename}_{timestamp}.txt"
        
        # Create commit message
        commit_message = f"Add extracted content from {filename} - {file_type}"
        
        # Create or update file
        try:
            # Try to get existing file
            existing_file = repo.get_contents(github_filename)
            # Update existing file
            repo.update_file(
                path=github_filename,
                message=commit_message,
                content=content,
                sha=existing_file.sha
            )
        except:
            # Create new file
            repo.create_file(
                path=github_filename,
                message=commit_message,
                content=content
            )
        
        return {
            "success": True, 
            "message": f"Content synced to GitHub successfully!",
            "file_url": f"https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/blob/main/{github_filename}"
        }
        
    except Exception as e:
        return {"success": False, "message": f"Error syncing to GitHub: {str(e)}"}

def get_github_repo_info():
    """Get information about the connected GitHub repository"""
    if not github_client or not GITHUB_REPO_OWNER:
        return {"connected": False, "message": "GitHub not configured"}
    
    try:
        repo = github_client.get_repo(f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
        return {
            "connected": True,
            "repo_name": repo.name,
            "repo_url": repo.html_url,
            "owner": repo.owner.login,
            "description": repo.description or "No description",
            "last_updated": repo.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        return {"connected": False, "message": f"Error connecting to repository: {str(e)}"}

def create_webhook():
    """Create a webhook for the repository"""
    if not github_client or not GITHUB_REPO_OWNER:
        return {"success": False, "message": "GitHub not configured"}
    
    try:
        repo = github_client.get_repo(f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
        
        # Webhook configuration - Railway will provide the URL
        webhook_url = os.getenv('RAILWAY_PUBLIC_DOMAIN', 'https://your-app-url.com')
        webhook_config = {
            "url": f"{webhook_url}/webhook",
            "content_type": "json",
            "secret": os.getenv('WEBHOOK_SECRET', 'your-webhook-secret')
        }
        
        # Create webhook
        webhook = repo.create_hook(
            name="web",
            config=webhook_config,
            events=["push", "pull_request"],
            active=True
        )
        
        return {"success": True, "webhook_id": webhook.id}
    except Exception as e:
        return {"success": False, "message": f"Error creating webhook: {str(e)}"}

@get("/")
def index():
    # Get GitHub repository info
    github_info = get_github_repo_info()
    
    return html(
        head(
            title("Busyness Chatbot - OCR & GitHub Sync"),
            meta(charset="utf-8"),
            meta(name="viewport", content="width=device-width, initial-scale=1"),
            link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css"),
            link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css")
        ),
        body(
            div(class_="container mt-4",
                div(class_="row",
                    div(class_="col-md-8",
                        div(class_="card",
                            div(class_="card-header bg-primary text-white d-flex justify-content-between align-items-center",
                                h1(class_="card-title mb-0", "Busyness Chatbot - OCR & GitHub Sync"),
                                div(class_="d-flex align-items-center",
                                    i(class_="bi bi-github me-2"),
                                    span("GitHub Integration")
                                )
                            ),
                            div(class_="card-body",
                                p(class_="text-muted", "Upload an image or PDF file to extract text using AI-powered OCR and sync with your GitHub repository"),
                                
                                # GitHub Status
                                div(class_="mb-4",
                                    div(class_="card bg-light",
                                        div(class_="card-body py-2",
                                            div(class_="d-flex justify-content-between align-items-center",
                                                div(
                                                    i(class_="bi bi-github me-2"),
                                                    strong("GitHub Repository Status")
                                                ),
                                                span(class_=f"badge {'bg-success' if github_info.get('connected') else 'bg-warning'}",
                                                     "Connected" if github_info.get('connected') else "Not Configured")
                                            ),
                                            div(id="github-info", class_="mt-2")
                                        )
                                    )
                                ),
                                
                                form(action="/upload", method="post", enctype="multipart/form-data",
                                    div(class_="mb-3",
                                        label(for_="file", class_="form-label", "Select File"),
                                        input(type="file", id="file", name="file", class_="form-control", 
                                              accept=".jpg,.jpeg,.png,.gif,.bmp,.pdf", required=True)
                                    ),
                                    div(class_="mb-3",
                                        div(class_="form-check",
                                            input(type="checkbox", id="sync-github", name="sync_github", class_="form-check-input", checked=True),
                                            label(for_="sync-github", class_="form-check-label", "Sync to GitHub repository")
                                        )
                                    ),
                                    div(class_="d-grid",
                                        button(type="submit", class_="btn btn-primary btn-lg", "Extract Text & Sync")
                                    )
                                ),
                                
                                div(id="result", class_="mt-4")
                            )
                        )
                    ),
                    div(class_="col-md-4",
                        div(class_="card",
                            div(class_="card-header bg-info text-white",
                                h5(class_="card-title mb-0", "GitHub Actions")
                            ),
                            div(class_="card-body",
                                div(class_="d-grid gap-2",
                                    button(type="button", class_="btn btn-outline-primary", onclick="checkGitHubStatus()",
                                           "Check GitHub Status"),
                                    button(type="button", class_="btn btn-outline-success", onclick="createWebhook()",
                                           "Setup Webhook"),
                                    a(href="/github-config", class_="btn btn-outline-secondary", "Configure GitHub")
                                ),
                                div(id="github-actions-result", class_="mt-3")
                            )
                        ),
                        div(class_="card mt-3",
                            div(class_="card-header bg-secondary text-white",
                                h6(class_="card-title mb-0", "Recent Extractions")
                            ),
                            div(class_="card-body",
                                div(id="recent-extractions", "No recent extractions")
                            )
                        )
                    )
                )
            ),
            script(src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"),
            script("""
                // Load GitHub info on page load
                document.addEventListener('DOMContentLoaded', function() {
                    loadGitHubInfo();
                });
                
                function loadGitHubInfo() {
                    fetch('/github-info')
                        .then(response => response.json())
                        .then(data => {
                            const infoDiv = document.getElementById('github-info');
                            if (data.connected) {
                                infoDiv.innerHTML = `
                                    <small class="text-muted">
                                        <strong>Repository:</strong> ${data.owner}/${data.repo_name}<br>
                                        <strong>Last Updated:</strong> ${data.last_updated}<br>
                                        <a href="${data.repo_url}" target="_blank" class="btn btn-sm btn-outline-primary mt-1">
                                            <i class="bi bi-box-arrow-up-right"></i> View Repository
                                        </a>
                                    </small>
                                `;
                            } else {
                                infoDiv.innerHTML = `
                                    <small class="text-warning">
                                        <i class="bi bi-exclamation-triangle"></i> ${data.message}
                                        <br><a href="/github-config" class="btn btn-sm btn-outline-warning mt-1">Configure</a>
                                    </small>
                                `;
                            }
                        });
                }
                
                function checkGitHubStatus() {
                    fetch('/github-info')
                        .then(response => response.json())
                        .then(data => {
                            const resultDiv = document.getElementById('github-actions-result');
                            if (data.connected) {
                                resultDiv.innerHTML = `
                                    <div class="alert alert-success">
                                        <i class="bi bi-check-circle"></i> Connected to ${data.owner}/${data.repo_name}
                                    </div>
                                `;
                            } else {
                                resultDiv.innerHTML = `
                                    <div class="alert alert-warning">
                                        <i class="bi bi-exclamation-triangle"></i> ${data.message}
                                    </div>
                                `;
                            }
                        });
                }
                
                function createWebhook() {
                    fetch('/create-webhook', {method: 'POST'})
                        .then(response => response.json())
                        .then(data => {
                            const resultDiv = document.getElementById('github-actions-result');
                            if (data.success) {
                                resultDiv.innerHTML = `
                                    <div class="alert alert-success">
                                        <i class="bi bi-check-circle"></i> Webhook created successfully!
                                    </div>
                                `;
                            } else {
                                resultDiv.innerHTML = `
                                    <div class="alert alert-danger">
                                        <i class="bi bi-x-circle"></i> ${data.message}
                                    </div>
                                `;
                            }
                        });
                }
            """)
        )
    )

@post("/upload")
def upload_file(request):
    try:
        # Get the uploaded file
        file = request.files.get("file")
        if not file:
            return html(
                div(class_="alert alert-danger", "No file uploaded"),
                script("document.getElementById('result').innerHTML = arguments[0].outerHTML;", 
                       div(class_="alert alert-danger", "No file uploaded"))
            )
        
        # Check if GitHub sync is requested
        sync_github = request.form.get("sync_github") == "on"
        
        # Read file data
        file_data = file.read()
        file_extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        
        # Process based on file type
        if file_extension in ['pdf']:
            extracted_text = extract_text_from_pdf(file_data)
        elif file_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
            extracted_text = extract_text_from_image(file_data)
        else:
            return html(
                div(class_="alert alert-warning", "Unsupported file type. Please upload an image or PDF file."),
                script("document.getElementById('result').innerHTML = arguments[0].outerHTML;", 
                       div(class_="alert alert-warning", "Unsupported file type. Please upload an image or PDF file."))
            )
        
        # Store extracted content
        content_id = f"{file.filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        extracted_content_store[content_id] = {
            "filename": file.filename,
            "content": extracted_text,
            "timestamp": datetime.now().isoformat(),
            "file_type": file_extension
        }
        
        # GitHub sync if requested
        github_sync_result = None
        if sync_github and extracted_text:
            github_sync_result = sync_to_github(extracted_text, file.filename, file_extension)
        
        # Build result HTML
        result_html = div(
            div(class_="alert alert-success", "Text extracted successfully!"),
            div(class_="card",
                div(class_="card-header d-flex justify-content-between align-items-center",
                    span("Extracted Text"),
                    small(class_="text-muted", f"File: {file.filename}")
                ),
                div(class_="card-body",
                    pre(class_="bg-light p-3", style="max-height: 400px; overflow-y: auto;", 
                        extracted_text if extracted_text else "No text found in the document.")
                )
            )
        )
        
        # Add GitHub sync result if applicable
        if sync_github:
            if github_sync_result and github_sync_result.get("success"):
                result_html += div(
                    div(class_="alert alert-info d-flex justify-content-between align-items-center",
                        div(
                            i(class_="bi bi-github me-2"),
                            span(github_sync_result["message"])
                        ),
                        a(href=github_sync_result.get("file_url", "#"), target="_blank", 
                          class_="btn btn-sm btn-outline-primary",
                          "View on GitHub")
                    )
                )
            elif github_sync_result:
                result_html += div(
                    div(class_="alert alert-warning",
                        i(class_="bi bi-exclamation-triangle me-2"),
                        github_sync_result["message"])
        )
        
        return html(
            result_html,
            script("document.getElementById('result').innerHTML = arguments[0].outerHTML;", result_html)
        )
        
    except Exception as e:
        error_html = div(class_="alert alert-danger", f"Error processing file: {str(e)}")
        return html(
            error_html,
            script("document.getElementById('result').innerHTML = arguments[0].outerHTML;", error_html)
        )

@get("/github-info")
def github_info():
    """API endpoint to get GitHub repository information"""
    return get_github_repo_info()

@post("/create-webhook")
def create_webhook_endpoint():
    """API endpoint to create a webhook"""
    return create_webhook()

@get("/github-config")
def github_config():
    """GitHub configuration page"""
    return html(
        head(
            title("GitHub Configuration - Busyness Chatbot"),
            meta(charset="utf-8"),
            meta(name="viewport", content="width=device-width, initial-scale=1"),
            link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css"),
            link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css")
        ),
        body(
            div(class_="container mt-5",
                div(class_="row justify-content-center",
                    div(class_="col-md-8",
                        div(class_="card",
                            div(class_="card-header bg-primary text-white",
                                h1(class_="card-title text-center mb-0", "GitHub Configuration")
                            ),
                            div(class_="card-body",
                                div(class_="alert alert-info",
                                    i(class_="bi bi-info-circle me-2"),
                                    "Configure your GitHub integration to sync extracted content with your repository."
                                ),
                                
                                div(class_="mb-4",
                                    h4("Setup Instructions"),
                                    ol(
                                        li("Create a GitHub Personal Access Token:"),
                                        ul(
                                            li("Go to GitHub Settings → Developer settings → Personal access tokens"),
                                            li("Generate a new token with 'repo' permissions"),
                                            li("Copy the token and set it as GITHUB_TOKEN environment variable")
                                        ),
                                        li("Set your GitHub username as GITHUB_REPO_OWNER environment variable"),
                                        li("Optionally set GITHUB_REPO_NAME (defaults to 'busyness-chatbot')")
                                    )
                                ),
                                
                                div(class_="mb-4",
                                    h4("Environment Variables"),
                                    div(class_="table-responsive",
                                        table(class_="table table-striped",
                                            thead(
                                                tr(
                                                    th("Variable"),
                                                    th("Description"),
                                                    th("Example")
                                                )
                                            ),
                                            tbody(
                                                tr(
                                                    td("GITHUB_TOKEN"),
                                                    td("Your GitHub Personal Access Token"),
                                                    td("ghp_xxxxxxxxxxxxxxxxxxxx")
                                                ),
                                                tr(
                                                    td("GITHUB_REPO_OWNER"),
                                                    td("Your GitHub username"),
                                                    td("yourusername")
                                                ),
                                                tr(
                                                    td("GITHUB_REPO_NAME"),
                                                    td("Repository name (optional)"),
                                                    td("busyness-chatbot")
                                                )
                                            )
                                        )
                                    )
                                ),
                                
                                div(class_="mb-4",
                                    h4("Current Configuration Status"),
                                    div(id="config-status", class="alert alert-secondary", "Checking configuration...")
                                ),
                                
                                div(class_="d-grid gap-2",
                                    a(href="/", class_="btn btn-primary", "Back to Main App"),
                                    button(type="button", class_="btn btn-outline-primary", onclick="checkConfig()", "Check Configuration")
                                )
                            )
                        )
                    )
                )
            ),
            script(src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"),
            script("""
                document.addEventListener('DOMContentLoaded', function() {
                    checkConfig();
                });
                
                function checkConfig() {
                    fetch('/github-info')
                        .then(response => response.json())
                        .then(data => {
                            const statusDiv = document.getElementById('config-status');
                            if (data.connected) {
                                statusDiv.className = 'alert alert-success';
                                statusDiv.innerHTML = `
                                    <i class="bi bi-check-circle"></i> 
                                    <strong>GitHub Connected Successfully!</strong><br>
                                    Repository: ${data.owner}/${data.repo_name}<br>
                                    Last Updated: ${data.last_updated}
                                `;
                            } else {
                                statusDiv.className = 'alert alert-warning';
                                statusDiv.innerHTML = `
                                    <i class="bi bi-exclamation-triangle"></i> 
                                    <strong>GitHub Not Configured</strong><br>
                                    ${data.message}
                                `;
                            }
                        })
                        .catch(error => {
                            const statusDiv = document.getElementById('config-status');
                            statusDiv.className = 'alert alert-danger';
                            statusDiv.innerHTML = `
                                <i class="bi bi-x-circle"></i> 
                                <strong>Error checking configuration</strong><br>
                                ${error.message}
                            `;
                        });
                }
            """)
        )
    )

@post("/webhook")
def github_webhook(request):
    """Handle GitHub webhooks for real-time sync"""
    try:
        # Get the webhook payload
        payload = request.json()
        
        # Log the webhook event
        print(f"Received GitHub webhook: {payload.get('action', 'unknown')}")
        
        # Handle different webhook events
        if payload.get('action') == 'opened' and 'pull_request' in payload:
            # New pull request opened
            pr = payload['pull_request']
            return {"status": "success", "message": f"Pull request #{pr['number']} opened: {pr['title']}"}
        
        elif payload.get('action') == 'created' and 'issue' in payload:
            # New issue created
            issue = payload['issue']
            return {"status": "success", "message": f"Issue #{issue['number']} created: {issue['title']}"}
        
        return {"status": "success", "message": "Webhook received"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Get port from environment variable (Railway sets this) or default to 5000
    port = int(os.getenv('PORT', 5000))
    # Run the application
    run(port=port, host='0.0.0.0')
