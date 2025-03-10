import os
import re
import logging
from langchain_groq import ChatGroq
from flask import Flask, render_template_string, request, send_file
from flask_cors import CORS
import subprocess
import imgkit
from dotenv import load_dotenv  # Import python-dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)
CORS(app)

# Get the Groq API Key from the environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logging.error("GROQ_API_KEY not found in environment variables.")
    raise ValueError("GROQ_API_KEY must be set in the .env file.")

# Initialize Langchain ChatGroq
llm = ChatGroq(
    model="mixtral-8x7b-32768",
    temperature=0.0,
    max_retries=2,
    groq_api_key=GROQ_API_KEY,
)

def generate_mermaid_code(project_description):
    """Generates Mermaid code from a project description using Groq LLM."""
    try:
        prompt = f"Create a Mermaid code diagram that visually represents the following project: {project_description}. Focus on the key components and their relationships. The diagram should illustrate the architecture and dependencies."
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        logging.error(f"Error generating Mermaid code: {e}")
        return None

def extract_mermaid_code(text):
    """Extracts Mermaid code from a text string using regex."""
    mermaid_pattern = r"```mermaid(.*?)```"
    match = re.search(mermaid_pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return None

def save_to_readme(mermaid_code):
    """Saves the Mermaid code to a readme.md file."""
    try:
        with open("readme.md", "w") as f:
            f.write("## Mermaid Diagram\n")
            f.write("```mermaid\n")
            f.write(mermaid_code)
            f.write("\n```\n")
        logging.info("Mermaid code saved to readme.md")
    except Exception as e:
        logging.error(f"Error saving to readme.md: {e}")
        return False
    return True

def convert_readme_to_png(readme_file="readme.md", output_png="mermaid_diagram.png"):
    """Converts the readme.md file containing Mermaid code to a PNG image."""
    try:
        # Specify the path to the wkhtmltopdf executable
        wkhtmltopdf_path = 'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltoimage.exe'  # Windows example
        # wkhtmltopdf_path = '/usr/local/bin/wkhtmltoimage'  # macOS example

        config = imgkit.config(wkhtmltoimage=wkhtmltopdf_path)

        # Read the mermaid code from readme.md
        with open(readme_file, 'r') as f:
            readme_content = f.read()

        # Extract mermaid code
        mermaid_code = extract_mermaid_code(readme_content)

        if not mermaid_code:
            logging.error("No Mermaid code found in readme.md")
            return False

        # Create an HTML template with mermaid code
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Mermaid Diagram</title>
            <script src="https://cdn.jsdelivr.net/npm/mermaid@10.2.0/dist/mermaid.min.js"></script>
            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    mermaid.initialize({{ startOnLoad: true }});
                }});
            </script>
        </head>
        <body>
            <div class="mermaid">
                {mermaid_code}
            </div>
        </body>
        </html>
        """

        # Save the HTML to a temporary file
        with open("temp.html", "w") as temp_file:
            temp_file.write(html_content)

        imgkit.from_file("temp.html", output_png, config=config)
        os.remove("temp.html")

        logging.info(f"Mermaid diagram saved to {output_png}")
        return True
    except Exception as e:
        logging.error(f"Error converting to PNG: {e}")
        return False

@app.route("/mermaid", methods=['POST'])
def mermaid_endpoint():
    # Expect a JSON payload with a 'project_description' key.
    data = request.get_json()
    if not data or 'project_description' not in data:
        return {"error": "JSON payload with 'project_description' key required."}, 400

    project_description = data['project_description']
    mermaid_code = None
    png_available = False

    mermaid_text = generate_mermaid_code(project_description)

    if mermaid_text:
        mermaid_code = extract_mermaid_code(mermaid_text)
        if mermaid_code:
            save_to_readme(mermaid_code)
            if convert_readme_to_png():
                png_available = True
            else:
                png_available = False
        else:
            mermaid_code = "Mermaid code not found in the response."
    else:
        mermaid_code = "Failed to generate Mermaid code."

    html_response = render_template_string("""
         <!DOCTYPE html>
        <html>                                  
        <h1>Mermaid Diagram Generator</h1>

        {% if mermaid_code %}
            <h2>Generated Mermaid Diagram:</h2>
            <div id="mermaid-diagram">
                <pre class="mermaid">
                    {{ mermaid_code }}
                </pre>
            </div>
        {% endif %}

        {% if png_available %}
            <h2>Mermaid Diagram (PNG):</h2>
            <img src="/get_png" alt="Mermaid Diagram">
        {% endif %}

        <script src="https://cdn.jsdelivr.net/npm/mermaid@10.2.0/dist/mermaid.min.js"></script>
        <script>
            mermaid.initialize({ startOnLoad: true });
        </script>
        </html>
    """, mermaid_code=mermaid_code, png_available=png_available)

    # Return the HTML response with the proper Content-Type header.
    return html_response, 200, {'Content-Type': 'text/html'}

@app.route('/get_png')
def get_png():
    """Serves the generated PNG image."""
    try:
        return send_file("mermaid_diagram.png", mimetype='image/png')
    except FileNotFoundError:
        return "PNG image not found.", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10002))
     app.run(host="0.0.0.0", port=port)
