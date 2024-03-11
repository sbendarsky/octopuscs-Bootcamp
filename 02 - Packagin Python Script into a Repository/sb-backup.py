import os 
import shutil
from datetime import datetime

config_file = "/opt/sb-backup/sb-backup.conf"
failure_log = "/backup/failure.log"
backup_directory = "/backup/"

def read_config():
    files = []
    try:
        with open(config_file, "r") as f:
            for line in f:
                files.append(line.strip())
    except FileNotFoundError:
        log_error("Config file not found")
    except Exception as e:
        log_error(f"Error reading config file: {str(e)}")
    return files

def backup_files(files):
    try:
        # Create backup directory if it doesn't exist
        os.makedirs(backup_directory, exist_ok=True)
    except Exception as e:
        log_error(f"Error creating backup directory: {str(e)}")
        return

    try:
        # Create timestamp for log and directory
        timestamp = datetime.now()
        log_directory = os.path.join(backup_directory, timestamp.strftime("%Y-%m-%d-%H-%M"))
        os.makedirs(log_directory, exist_ok=True)
        
        for file in files:
            try:
                # Copy file to log directory
                shutil.copy(file, os.path.join(log_directory, os.path.basename(file)))
            except Exception as e:
                log_error(f"Error backing up file: {file} - {str(e)}")
    except Exception as e:
        log_error(f"Error in backup process: {str(e)}")

def log_error(message):
    os.makedirs(backup_directory, exist_ok=True)  
    # Log error to failure log file
    with open(failure_log, "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{timestamp} - {message}\n")
    print(f"Error: {message}")

if __name__ == "__main__":
    files = read_config()
    backup_files(files)
