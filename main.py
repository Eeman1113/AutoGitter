import os
import sys
import time
import shutil
from datetime import datetime
import json
import getpass
from pathlib import Path

# Configuration
WORK_DIR = "/Users/eemanmajumder/code_shit"
GITHUB_USERNAME = "eeman1113"
NUM_FOLDERS = 10

def get_groq_api_key():
    """Get the Groq API key securely."""
    # First check environment variables
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key:
        return api_key
    
    # Otherwise, use the provided key (in production, should prompt instead)(TOO BAD WONT WORK)
    return "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" 

def get_github_token():
    """Get GitHub token securely."""
    # First check environment variables
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    
    # Otherwise, ask for it
    print("\nYou need a GitHub personal access token to create repositories.")
    print("If you don't have one, create one at: https://github.com/settings/tokens")
    print("Make sure to include the 'repo' scope for full repository access.")
    
    return getpass.getpass("Enter your GitHub personal access token: ")

def get_last_modified_folders(directory, num_folders=10):
    """Get the last N modified folders in the given directory."""
    folders = []
    
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            modified_time = os.path.getmtime(item_path)
            folders.append((item_path, modified_time))
    
    # Sort by modification time (newest first)
    folders.sort(key=lambda x: x[1], reverse=True)
    
    # Return the first N folders
    return [folder[0] for folder in folders[:num_folders]]

def is_salvageable_project(folder_path):
    """Check if a folder contains a salvageable project."""
    # Ignore typical non-project directories
    basename = os.path.basename(folder_path)
    if basename.startswith('.') or basename in ['node_modules', 'venv', 'env', '__pycache__']:
        return False
        
    # Check if the folder has code files
    code_extensions = {'.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.go', '.rs', '.ts', '.rb', '.php'}
    
    for root, _, files in os.walk(folder_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in code_extensions:
                return True
    
    return False

def analyze_project(folder_path):
    """Analyze a project folder to get a summary of its contents."""
    summary = {
        "folder_name": os.path.basename(folder_path),
        "files_count": 0,
        "languages": {},
        "file_types": {},
        "last_modified": datetime.fromtimestamp(os.path.getmtime(folder_path)).strftime('%Y-%m-%d %H:%M:%S'),
        "size_kb": 0
    }
    
    for root, _, files in os.walk(folder_path):
        # Skip hidden directories and common non-project directories
        if any(part.startswith('.') or part in ['node_modules', 'venv', 'env', '__pycache__'] 
               for part in Path(root).parts):
            continue
            
        for file in files:
            # Skip hidden files
            if file.startswith('.'):
                continue
                
            file_path = os.path.join(root, file)
            if os.path.isfile(file_path):
                summary["files_count"] += 1
                
                # Get file extension and update file types
                ext = os.path.splitext(file)[1].lower()
                if ext:
                    summary["file_types"][ext] = summary["file_types"].get(ext, 0) + 1
                    
                    # Map extensions to languages
                    lang_map = {
                        ".py": "Python",
                        ".js": "JavaScript",
                        ".jsx": "React",
                        ".ts": "TypeScript",
                        ".tsx": "React TypeScript",
                        ".html": "HTML",
                        ".css": "CSS",
                        ".scss": "SCSS",
                        ".sass": "Sass",
                        ".java": "Java",
                        ".cpp": "C++",
                        ".c": "C",
                        ".go": "Go",
                        ".rs": "Rust",
                        ".rb": "Ruby",
                        ".php": "PHP",
                        ".swift": "Swift",
                        ".kt": "Kotlin",
                        ".sql": "SQL",
                        ".json": "JSON",
                        ".md": "Markdown"
                    }
                    
                    if ext in lang_map:
                        lang = lang_map[ext]
                        summary["languages"][lang] = summary["languages"].get(lang, 0) + 1
                
                # Update size
                try:
                    summary["size_kb"] += os.path.getsize(file_path) / 1024
                except:
                    pass
    
    summary["size_kb"] = round(summary["size_kb"], 2)
    
    return summary

def generate_project_name_and_readme_with_groq(project_summary, api_key):
    """Use Groq API to generate a project name and README."""
    try:
        import requests
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""
        I have a coding project with the following characteristics:
        - Original folder name: {project_summary['folder_name']}
        - Contains {project_summary['files_count']} files
        - Programming languages used: {', '.join(project_summary['languages'].keys()) if project_summary['languages'] else 'Unknown'}
        - File types: {', '.join(f"{k} ({v} files)" for k, v in project_summary['file_types'].items())}
        - Last modified: {project_summary['last_modified']}
        - Size: {project_summary['size_kb']} KB
        
        Based on this information:
        1. Suggest a professional, concise name for this project (only the name, no explanations)
        2. Write a comprehensive README.md file for a GitHub repository containing this project.
        
        The README should include:
        - A clear title (using the project name you suggested)
        - A brief description of what the project likely does
        - A "Features" section
        - Installation and usage instructions
        - A "Contributing" section
        - A license statement (suggest MIT License)
        
        Format your response as a JSON with two fields:
        "project_name": "Your suggested name",
        "readme_content": "The full README.md content"
        """
        
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 1,
            "max_tokens": 1024,
            "top_p": 1
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            try:
                response_json = response.json()
                content = response_json["choices"][0]["message"]["content"]
                
                # Extract JSON from response
                if '{' in content and '}' in content:
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    json_str = content[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    result = json.loads(content)
                    
                return result
            except Exception as e:
                print(f"Error parsing Groq response: {e}")
        else:
            print(f"Error from Groq API: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Failed to use Groq API: {e}")
    
    # Fallback to simple naming if Groq API fails
    return generate_fallback_name_and_readme(project_summary)

def generate_fallback_name_and_readme(project_summary):
    """Generate a basic project name and README when AI is unavailable."""
    folder_name = project_summary['folder_name']
    languages = list(project_summary['languages'].keys())
    
    # Generate a simple project name
    if languages:
        main_language = max(project_summary['languages'].items(), key=lambda x: x[1])[0]
        project_name = f"{main_language.lower()}-{folder_name}"
    else:
        project_name = f"project-{folder_name}"
    
    # Make it safe
    project_name = ''.join(c if c.isalnum() or c in ['-', '_'] else '-' for c in project_name)
    
    # Generate a basic README
    tech_stack = ", ".join(languages) if languages else "various technologies"
    readme_content = f"""# {project_name}

## Overview
A project using {tech_stack}, salvaged from earlier work.

## Features
- Code organization and structure
- Implementation of {tech_stack} functionality

## Installation
1. Clone this repository
2. Install dependencies (if applicable)
3. Run the project according to the included source files

## Usage
Refer to source code for specific usage instructions.

## Contributing
Contributions are welcome. Please feel free to submit a Pull Request.

## License
This project is licensed under the MIT License - see the LICENSE file for details.
"""
    
    return {
        "project_name": project_name,
        "readme_content": readme_content
    }

def create_github_repo(repo_name, github_token, is_private=False):
    """Create a new GitHub repository using os.system()."""
    try:
        # Replace spaces with hyphens and remove special characters for a valid repo name
        safe_repo_name = ''.join(c if c.isalnum() or c in ['-', '_'] else '-' for c in repo_name.replace(' ', '-'))
        
        # Create private/public flag
        visibility = "--private" if is_private else "--public"
        
        # Use GitHub CLI if available (recommended)
        if os.system("which gh > /dev/null 2>&1") == 0:
            # GitHub CLI is available
            print("Using GitHub CLI to create repository...")
            os.environ["GITHUB_TOKEN"] = github_token
            create_cmd = f'gh repo create {safe_repo_name} {visibility} --description "Salvaged project: {repo_name}" --confirm'
            if os.system(create_cmd) != 0:
                print("Failed to create repository using GitHub CLI")
                return None, None
        else:
            # Use curl as a fallback
            print("GitHub CLI not found, using curl instead...")
            visibility_value = "true" if is_private else "false"
            curl_cmd = f'''
            curl -s -X POST https://api.github.com/user/repos \
                -H "Authorization: token {github_token}" \
                -H "Accept: application/vnd.github.v3+json" \
                -d '{{"name":"{safe_repo_name}", "description":"Salvaged project: {repo_name}", "private":{visibility_value}}}'
            '''
            if os.system(curl_cmd) != 0:
                print("Failed to create repository using curl")
                return None, None
        
        # Return the repository URL and the safe name
        repo_url = f"https://github.com/{GITHUB_USERNAME}/{safe_repo_name}.git"
        return repo_url, safe_repo_name
        
    except Exception as e:
        print(f"Error creating GitHub repository: {e}")
        return None, None

def git_init_and_push(source_dir, target_dir, repo_url, github_username, github_token):
    """Initialize git, add files, and push to GitHub using os.system()."""
    os.chdir(target_dir)
    
    try:
        # Initialize git repo
        print("Initializing Git repository...")
        os.system("git init")
        
        # Add all files
        print("Adding files to Git...")
        os.system("git add .")
        
        # Configure user
        os.system(f"git config user.email '{github_username}@users.noreply.github.com'")
        os.system(f"git config user.name '{github_username}'")
        
        # Commit
        print("Committing files...")
        os.system("git commit -m 'Initial commit - Salvaged project'")
        
        # Add remote and push (using main branch)
        os.system("git branch -M main")
        os.system(f"git remote add origin {repo_url}")
        
        # Set up credentials for push
        print("Setting up credentials for push...")
        if "GITHUB_TOKEN" not in os.environ:
            os.environ["GITHUB_TOKEN"] = github_token
        
        # Create a temporary credentials file
        credentials_path = os.path.join(target_dir, ".git", "credentials")
        os.makedirs(os.path.dirname(credentials_path), exist_ok=True)
        
        # Use credential helper for HTTPS
        os.system("git config --local credential.helper 'store --file=.git/credentials'")
        with open(credentials_path, "w") as f:
            f.write(f"https://{github_username}:{github_token}@github.com\n")
        
        # Push to GitHub
        print("Pushing to GitHub...")
        push_result = os.system("git push -u origin main")
        
        # Clean up credentials
        print("Cleaning up credentials...")
        if os.path.exists(credentials_path):
            os.remove(credentials_path)
        
        return push_result == 0
        
    except Exception as e:
        print(f"Git operation failed: {e}")
        return False

def salvage_project(folder_path, groq_api_key, github_token, github_username, is_private=False):
    """Analyze, refactor, and push a salvageable project to GitHub."""
    print(f"\nAnalyzing project in folder: {os.path.basename(folder_path)}")
    
    # Analyze the project
    project_summary = analyze_project(folder_path)
    print(f"Project summary: {len(project_summary['file_types'])} file types, {project_summary['files_count']} files")
    
    # Generate project name and README using the direct API approach (avoiding the client library)
    result = generate_project_name_and_readme_with_groq(project_summary, groq_api_key)
    project_name = result["project_name"]
    readme_content = result["readme_content"]
    
    print(f"Generated project name: {project_name}")
    
    # Create GitHub repository
    repo_url, safe_repo_name = create_github_repo(project_name, github_token, is_private)
    if not repo_url:
        print("Failed to create GitHub repository. Stopping.")
        return False
    
    # Create target directory (using safe repo name)
    target_dir = os.path.join(os.path.dirname(folder_path), safe_repo_name)
    if os.path.exists(target_dir):
        target_dir = f"{target_dir}_{int(time.time())}"  # Add timestamp to make unique
        
    os.makedirs(target_dir, exist_ok=True)
    
    # Copy the project files
    print("Copying project files...")
    for item in os.listdir(folder_path):
        # Skip hidden files and common directories to exclude
        if item.startswith('.') or item in ['node_modules', 'venv', 'env', '__pycache__', 'build', 'dist']:
            continue
            
        s = os.path.join(folder_path, item)
        d = os.path.join(target_dir, item)
        try:
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        except Exception as e:
            print(f"Warning: Could not copy {item}: {e}")
    
    # Create README file
    print("Creating README.md...")
    with open(os.path.join(target_dir, "README.md"), "w") as f:
        f.write(readme_content)
    
    # Push to GitHub
    success = git_init_and_push(folder_path, target_dir, repo_url, github_username, github_token)
    if success:
        print(f"Successfully pushed project to GitHub: {repo_url}")
        return True
    else:
        print("Failed to push to GitHub.")
        return False

def main():
    print("Project Salvager - Find and salvage coding projects")
    print("---------------------------------------------------")
    
    # Get API keys and tokens
    try:
        groq_api_key = get_groq_api_key()
        github_token = get_github_token()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    
    # Get the last modified folders
    print(f"Finding the last {NUM_FOLDERS} modified folders in {WORK_DIR}...")
    folders = get_last_modified_folders(WORK_DIR, NUM_FOLDERS)
    
    print(f"Found {len(folders)} folders.")
    
    # Check each folder for salvageable projects
    salvageable_count = 0
    for folder in folders:
        folder_name = os.path.basename(folder)
        print(f"Checking folder: {folder_name}")
        
        if is_salvageable_project(folder):
            print(f"Found salvageable project in: {folder_name}")
            
            # Ask if this should be salvaged
            should_salvage = input(f"Do you want to salvage {folder_name}? (y/n): ").strip().lower()
            if should_salvage != 'y':
                print(f"Skipping {folder_name}")
                continue
                
            # Ask if this should be private
            is_private = input(f"Should the repository for {folder_name} be private? (y/n): ").strip().lower() == 'y'
            
            # Salvage the project
            if salvage_project(folder, groq_api_key, github_token, GITHUB_USERNAME, is_private):
                salvageable_count += 1
    
    print(f"\nCompleted! Salvaged {salvageable_count} projects.")

if __name__ == "__main__":
    main()
