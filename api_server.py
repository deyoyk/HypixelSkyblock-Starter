import os
import sys
import time
import subprocess
import logging
import platform
import signal
import atexit
import shutil
import json
import urllib.request
import threading
import yaml
import toml
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from enum import Enum

class ServiceType(Enum):
    API = "ServiceAPI.jar"
    AUCTION_HOUSE = "ServiceAuctionHouse.jar"
    BAZAAR = "ServiceBazaar.jar"
    DARK_AUCTION = "ServiceDarkAuction.jar"
    DATA_MUTEX = "ServiceDataMutex.jar"
    FRIEND = "ServiceFriend.jar"
    ITEM_TRACKER = "ServiceItemTracker.jar"
    ORCHESTRATOR = "ServiceOrchestrator.jar"

ALL_SERVER_TYPES = [
    (0, "SKYBLOCK_HUB"),
    (0, "SKYBLOCK_ISLAND"),
    (0, "SKYBLOCK_SPIDERS_DEN"),
    (0, "SKYBLOCK_THE_END"),
    (0, "SKYBLOCK_CRIMSON_ISLE"),
    (0, "SKYBLOCK_DUNGEON_HUB"),
    (0, "SKYBLOCK_DUNGEON"),
    (0, "SKYBLOCK_FARMING_ISLANDS"),
    (0, "SKYBLOCK_GOLD_MINE"),
    (0, "SKYBLOCK_DEEP_CAVERNS"),
    (0, "SKYBLOCK_DWARVEN_MINES"),
    (0, "SKYBLOCK_CRYSTAL_HOLLOWS"),
    (0, "SKYBLOCK_THE_PARK"),
    (0, "SKYBLOCK_JERRYS_WORKSHOP"),
    (0, "SKYBLOCK_BACKWATER_BAYOU"),
    (0, "SKYBLOCK_GALATEA"),
    (1, "PROTOTYPE_LOBBY"),
    (1, "BEDWARS_LOBBY"),
    (0, "BEDWARS_GAME"),
    (0, "BEDWARS_CONFIGURATOR"),
    (0, "MURDER_MYSTERY_LOBBY"),
    (0, "MURDER_MYSTERY_GAME"),
    (0, "MURDER_MYSTERY_CONFIGURATOR"),
    (0, "SKYWARS_LOBBY"),
    (0, "SKYWARS_GAME"),
    (0, "SKYWARS_CONFIGURATOR"),
]

class ProcessManager:
    def __init__(self):
        self.processes = []

    def add(self, p, name):
        self.processes.append((p, name))
        logging.info(f"Started {name} PID={p.pid}")

    def cleanup(self):
        logging.info("Shutting down all processes")
        for p, name in self.processes:
            if p.poll() is None:
                logging.info(f"Stopping {name}")
                p.terminate()
                try:
                    p.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logging.warning(f"Force killing {name}")
                    p.kill()
        self.kill_java()

    @staticmethod
    def kill_java():
        logging.info("Killing leftover java processes")
        try:
            if platform.system().lower() == "windows":
                subprocess.run(["taskkill", "/F", "/IM", "java.exe"], capture_output=True)
            else:
                subprocess.run(["pkill", "-f", "java -jar"], capture_output=True)
        except Exception as e:
            logging.error(str(e))

class FileManager:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.config_dir = os.path.join(base_dir, "configuration")
        self.proxy_dir = os.path.join(base_dir, "proxy")
        self.gameserver_dir = os.path.join(base_dir, "gameserver")
        self.limbo_dir = os.path.join(base_dir, "limbo")
        self.services_dir = os.path.join(base_dir, "services")
        self.logs_dir = os.path.join(base_dir, "logs")

    def copy_file_if_not_exists(self, src, dst):
        if not os.path.exists(dst) and os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            logging.info(f"Copied {src} -> {dst}")

class ServiceStarter:
    def __init__(self, base_dir, config_dir, proxy_dir, limbo_dir, services_dir, gameserver_dir, logs_dir, proc_mgr):
        self.base_dir = base_dir
        self.config_dir = config_dir
        self.proxy_dir = proxy_dir
        self.limbo_dir = limbo_dir
        self.services_dir = services_dir
        self.gameserver_dir = gameserver_dir
        self.logs_dir = logs_dir
        self.proc_mgr = proc_mgr

    def start_proxy(self):
        jar = os.path.join(self.proxy_dir, "velocity.jar")
        if not os.path.isfile(jar):
            logging.warning("Proxy velocity jar missing")
            return
        log = open(os.path.join(self.logs_dir, "velocity.log"), "a")
        p = subprocess.Popen(
            ["java", "-jar", "velocity.jar"],
            cwd=self.proxy_dir,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        self.proc_mgr.add(p, "Proxy")

    def start_nanolimbo(self):
        jar = os.path.join(self.limbo_dir, "NanoLimbo.jar")
        if not os.path.isfile(jar):
            logging.warning("NanoLimbo jar missing")
            return
        log = open(os.path.join(self.logs_dir, "NanoLimbo.log"), "a")
        p = subprocess.Popen(
            ["java", "-jar", "NanoLimbo.jar"],
            cwd=self.limbo_dir,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        self.proc_mgr.add(p, "NanoLimbo")

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("api_server.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

LOG_FILE = "api_server.log"
process_manager = ProcessManager()
base_dir = os.path.dirname(os.path.abspath(__file__))
config_dir = os.path.join(base_dir, "configuration")
proxy_dir = os.path.join(base_dir, "proxy")
limbo_dir = os.path.join(base_dir, "limbo")
services_dir = os.path.join(base_dir, "services")
gameserver_dir = os.path.join(base_dir, "gameserver")
logs_dir = os.path.join(base_dir, "logs")

file_mgr = FileManager(base_dir)
starter = ServiceStarter(base_dir, config_dir, proxy_dir, limbo_dir, services_dir, gameserver_dir, logs_dir, process_manager)

os.makedirs(logs_dir, exist_ok=True)
os.makedirs(config_dir, exist_ok=True)

setup_logging()

instance_tracker = set()
download_status = {"status": "idle", "progress": 0, "current": "", "errors": []}
download_lock = threading.Lock()

class Downloader:
    def __init__(self, base_dir, force_download=False):
        self.base_dir = base_dir
        self.force_download = force_download
        self.release_base = "https://github.com/Swofty-Developments/HypixelSkyBlock/releases/download/latest"
        self.config_dir = os.path.join(base_dir, "configuration")
        self.services_dir = os.path.join(base_dir, "services")
        self.downloads_dir = os.path.join(base_dir, "downloads")
        os.makedirs(self.downloads_dir, exist_ok=True)

    def fetch(self, url, path):
        filename = os.path.basename(path)
        download_path = os.path.join(self.downloads_dir, filename)
        
        with download_lock:
            download_status["current"] = filename
        
        if os.path.exists(download_path) and not self.force_download:
            logging.info(f"Exists in downloads: {download_path}")
        else:
            os.makedirs(self.downloads_dir, exist_ok=True)
            logging.info(f"Downloading {url} to {download_path}")
            try:
                urllib.request.urlretrieve(url, download_path)
            except Exception as e:
                with download_lock:
                    download_status["errors"].append(f"Failed to download {filename}: {str(e)}")
                raise
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path) or self.force_download:
            shutil.copy2(download_path, path)
            logging.info(f"Copied {download_path} -> {path}")

    def download_services(self, selected=None):
        total = len(ServiceType) if not selected else len(selected)
        completed = 0
        
        with download_lock:
            download_status["status"] = "downloading"
            download_status["progress"] = 0
            download_status["errors"] = []
        
        try:
            services_to_download = selected if selected else ServiceType
            for s in services_to_download:
                if isinstance(s, str):
                    s = ServiceType[s.upper().replace('.JAR', '')]
                try:
                    self.fetch(
                        f"{self.release_base}/{s.value}",
                        os.path.join(self.services_dir, s.value),
                    )
                    completed += 1
                    with download_lock:
                        download_status["progress"] = int((completed / total) * 100)
                except Exception as e:
                    logging.error(f"Error downloading {s.value}: {str(e)}")
            
            self.fetch(
                f"{self.release_base}/HypixelCore.jar",
                os.path.join(self.services_dir, "HypixelCore.jar"),
            )
            
            self.fetch(
                "https://github.com/Swofty-Developments/HypixelSkyBlock/releases/download/latest/SkyBlockProxy.jar",
                os.path.join(self.config_dir, "SkyBlockProxy.jar"),
            )
            
            with download_lock:
                download_status["status"] = "completed"
                download_status["progress"] = 100
        except Exception as e:
            with download_lock:
                download_status["status"] = "error"
                download_status["errors"].append(str(e))
            logging.error(f"Download error: {str(e)}")

def get_server_status():
    status = {}
    for p, name in process_manager.processes:
        is_running = p.poll() is None
        status[name] = {
            "running": is_running,
            "pid": p.pid if is_running else None
        }
        if name not in instance_tracker:
            instance_tracker.add(name)
    
    for tracked_name in instance_tracker:
        if tracked_name not in status:
            status[tracked_name] = {
                "running": False,
                "pid": None
            }
    
    return status

def broadcast_server_status():
    try:
        status = get_server_status()
        result = {
            "proxy": {"id": "proxy", "name": "Proxy", "type": "proxy", "running": status.get("Proxy", {}).get("running", False)},
            "limbo": {"id": "nanolimbo", "name": "NanoLimbo", "type": "limbo", "running": status.get("NanoLimbo", {}).get("running", False)},
            "services": [],
            "gameservers": {}
        }
        
        for s in ServiceType:
            name = s.value.replace('.jar', '')
            result["services"].append({
                "id": name.lower(),
                "name": name,
                "type": "service",
                "running": status.get(s.value, {}).get("running", False)
            })
        
        for enabled, server in ALL_SERVER_TYPES:
            server_name = server
            server_lower = server.lower()
            if server_lower not in result["gameservers"]:
                result["gameservers"][server_lower] = {
                    "name": server_name,
                    "instances": []
                }
            
            instances = []
            for tracked_name in instance_tracker:
                if tracked_name.startswith(server_name + "_"):
                    try:
                        instance_num = int(tracked_name.split("_", 1)[1])
                        instances.append({
                            "id": f"{server_lower}_{instance_num}",
                            "instance": instance_num,
                            "running": status.get(tracked_name, {}).get("running", False)
                        })
                    except ValueError:
                        continue
            
            if not instances:
                instances.append({
                    "id": f"{server_lower}_0",
                    "instance": 0,
                    "running": False
                })
            
            instances.sort(key=lambda x: x["instance"])
            result["gameservers"][server_lower]["instances"] = instances
        
        socketio.emit('server_status', result)
    except Exception as e:
        logging.error(f"Error broadcasting server status: {str(e)}")

@socketio.on('connect')
def handle_connect():
    emit('connected', {'data': 'Connected'})
    broadcast_server_status()

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Server is running"}), 200

@app.route('/api/servers', methods=['GET', 'OPTIONS'])
def list_servers():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        status = get_server_status()
        result = {
            "proxy": {"id": "proxy", "name": "Proxy", "type": "proxy", "running": status.get("Proxy", {}).get("running", False)},
            "limbo": {"id": "nanolimbo", "name": "NanoLimbo", "type": "limbo", "running": status.get("NanoLimbo", {}).get("running", False)},
            "services": [],
            "gameservers": {}
        }
        
        for s in ServiceType:
            name = s.value.replace('.jar', '')
            result["services"].append({
                "id": name.lower(),
                "name": name,
                "type": "service",
                "running": status.get(s.value, {}).get("running", False)
            })
        
        for enabled, server in ALL_SERVER_TYPES:
            server_name = server
            if server_name not in result["gameservers"]:
                result["gameservers"][server_name] = {
                    "name": server_name,
                    "instances": []
                }
            
            instances = []
            max_instance = -1
            
            for instance_name, instance_status in status.items():
                if instance_name.startswith(f"{server_name}_"):
                    try:
                        instance_num = int(instance_name.split('_')[-1])
                        instances.append({
                            "id": f"{server_name.lower()}_{instance_num}",
                            "instance": instance_num,
                            "running": instance_status.get("running", False)
                        })
                        max_instance = max(max_instance, instance_num)
                    except ValueError:
                        pass
            
            if len(instances) == 0:
                instances.append({
                    "id": f"{server_name.lower()}_0",
                    "instance": 0,
                    "running": False
                })
            else:
                instances.sort(key=lambda x: x["instance"])
            
            result["gameservers"][server_name]["instances"] = instances
    
        return jsonify(result)
    except Exception as e:
        logging.error(f"Error listing servers: {str(e)}")
        return jsonify({
            "proxy": {"id": "proxy", "name": "Proxy", "type": "proxy", "running": False},
            "limbo": {"id": "nanolimbo", "name": "NanoLimbo", "type": "limbo", "running": False},
            "services": [],
            "gameservers": {}
        }), 500

@app.route('/api/servers/<server_id>/start', methods=['POST'])
def start_server(server_id):
    try:
        status = get_server_status()
        
        if server_id == "proxy":
            if status.get("Proxy", {}).get("running", False):
                return jsonify({"error": "Proxy is already running"}), 400
            starter.start_proxy()
            instance_tracker.add("Proxy")
            threading.Timer(0.5, broadcast_server_status).start()
            return jsonify({"message": "Proxy started"})
        
        elif server_id == "nanolimbo":
            if status.get("NanoLimbo", {}).get("running", False):
                return jsonify({"error": "NanoLimbo is already running"}), 400
            starter.start_nanolimbo()
            instance_tracker.add("NanoLimbo")
            threading.Timer(0.5, broadcast_server_status).start()
            return jsonify({"message": "NanoLimbo started"})
        
        else:
            service_found = False
            for s in ServiceType:
                service_id = s.value.replace('.jar', '').lower()
                if server_id == service_id:
                    service_found = True
                    if status.get(s.value, {}).get("running", False):
                        return jsonify({"error": f"{s.value} is already running"}), 400
                    jar = os.path.join(services_dir, s.value)
                    if not os.path.isfile(jar):
                        return jsonify({"error": f"{s.value} missing"}), 404
                    log = open(os.path.join(logs_dir, f"{s.value.replace('.jar', '.log')}"), "a")
                    p = subprocess.Popen(
                        ["java", "-Xms256M", "-Xmx512M", "-jar", s.value],
                        cwd=services_dir,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                    )
                    process_manager.add(p, s.value)
                    instance_tracker.add(s.value)
                    threading.Timer(0.5, broadcast_server_status).start()
                    return jsonify({"message": f"{s.value} started"})
            
            if not service_found:
                parts = server_id.rsplit('_', 1)
                if len(parts) == 2:
                    server_name = parts[0].upper()
                    instance = int(parts[1])
                    server_exists = any(server == server_name for _, server in ALL_SERVER_TYPES)
                    if server_exists:
                        if status.get(f"{server_name}_{instance}", {}).get("running", False):
                            return jsonify({"error": f"{server_name} {instance} is already running"}), 400
                        core = os.path.join(gameserver_dir, "HypixelCore.jar")
                        if not os.path.isfile(core):
                            return jsonify({"error": f"HypixelCore.jar missing"}), 404
                        log = open(os.path.join(logs_dir, f"{server_name}_{instance}.log"), "a")
                        p = subprocess.Popen(
                            ["java", "-Xms1G", "-Xmx2G", "-jar", "HypixelCore.jar", server_name],
                            cwd=gameserver_dir,
                            stdout=log,
                            stderr=subprocess.STDOUT,
                        )
                        instance_name = f"{server_name}_{instance}"
                        process_manager.add(p, instance_name)
                        instance_tracker.add(instance_name)
                        threading.Timer(0.5, broadcast_server_status).start()
                        return jsonify({"message": f"{server_name} {instance} started"})
                return jsonify({"error": "Server not found"}), 404
    
    except Exception as e:
        logging.error(f"Error starting server {server_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<server_id>/stop', methods=['POST'])
def stop_server(server_id):
    try:
        status = get_server_status()
        found = False
        target_name = None
        
        if server_id == "proxy":
            target_name = "Proxy"
        elif server_id == "nanolimbo":
            target_name = "NanoLimbo"
        else:
            for s in ServiceType:
                service_id = s.value.replace('.jar', '').lower()
                if server_id == service_id:
                    target_name = s.value
                    break
            
            if not target_name:
                parts = server_id.rsplit('_', 1)
                if len(parts) == 2:
                    server_name = parts[0].upper()
                    instance = int(parts[1])
                    target_name = f"{server_name}_{instance}"
        
        if target_name:
            for p, name in process_manager.processes[:]:
                if name == target_name:
                    if p.poll() is None:
                        logging.info(f"Stopping {name}")
                        p.terminate()
                        try:
                            p.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            logging.warning(f"Force killing {name}")
                            p.kill()
                        process_manager.processes.remove((p, name))
                        found = True
                        threading.Timer(0.5, broadcast_server_status).start()
                        return jsonify({"message": f"{name} stopped"})
        
        if not found:
            return jsonify({"error": "Server not found or not running"}), 404
        
    except Exception as e:
        logging.error(f"Error stopping server {server_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<server_id>/remove', methods=['POST'])
def remove_instance(server_id):
    try:
        target_name = None
        
        for enabled, server in ALL_SERVER_TYPES:
            server_lower = server.lower()
            if server_id.startswith(server_lower + '_'):
                try:
                    instance_num = int(server_id.rsplit('_', 1)[-1])
                    target_name = f"{server}_{instance_num}"
                    break
                except (ValueError, IndexError):
                    continue
        
        if not target_name:
            parts = server_id.rsplit('_', 1)
            if len(parts) == 2:
                try:
                    instance = int(parts[1])
                    server_name = parts[0].upper()
                    for enabled, server in ALL_SERVER_TYPES:
                        if server == server_name:
                            target_name = f"{server_name}_{instance}"
                            break
                except ValueError:
                    pass
        
        if not target_name:
            return jsonify({"error": f"Invalid server ID: {server_id}"}), 400
        
        removed_from_processes = False
        for p, name in process_manager.processes[:]:
            if name == target_name:
                if p.poll() is None:
                    logging.info(f"Stopping {name} before removal")
                    p.terminate()
                    try:
                        p.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        logging.warning(f"Force killing {name}")
                        p.kill()
                process_manager.processes.remove((p, name))
                removed_from_processes = True
        
        removed_from_tracker = False
        if target_name in instance_tracker:
            instance_tracker.remove(target_name)
            removed_from_tracker = True
            logging.info(f"Removed {target_name} from tracking")
        
        if removed_from_processes or removed_from_tracker:
            threading.Timer(0.5, broadcast_server_status).start()
            return jsonify({"message": f"{target_name} removed"})
        else:
            return jsonify({"error": "Instance not found"}), 404
        
    except Exception as e:
        logging.error(f"Error removing instance {server_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(get_server_status())

def get_log_file_path(server_id):
    if server_id == "proxy":
        return os.path.join(logs_dir, "velocity.log")
    elif server_id == "nanolimbo":
        return os.path.join(logs_dir, "NanoLimbo.log")
    else:
        for s in ServiceType:
            service_id = s.value.replace('.jar', '').lower()
            if server_id == service_id:
                return os.path.join(logs_dir, f"{s.value.replace('.jar', '.log')}")
        
        parts = server_id.rsplit('_', 1)
        if len(parts) == 2:
            server_name = parts[0].upper()
            instance = int(parts[1])
            return os.path.join(logs_dir, f"{server_name}_{instance}.log")
    
    return None

@app.route('/api/servers/<server_id>/logs', methods=['GET'])
def get_logs(server_id):
    try:
        log_path = get_log_file_path(server_id)
        if not log_path or not os.path.exists(log_path):
            return jsonify({"error": "Log file not found"}), 404
        
        lines = request.args.get('lines', default=500, type=int)
        tail = request.args.get('tail', default='true').lower() == 'true'
        
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            if tail:
                all_lines = f.readlines()
                log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            else:
                log_lines = [f.readline() for _ in range(lines) if f.readline()]
        
        return jsonify({
            "logs": log_lines,
            "total_lines": len(log_lines),
            "file_path": log_path
        })
    
    except Exception as e:
        logging.error(f"Error reading logs for {server_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<server_id>/logs/stream', methods=['GET'])
def stream_logs(server_id):
    try:
        log_path = get_log_file_path(server_id)
        if not log_path or not os.path.exists(log_path):
            return jsonify({"error": "Log file not found"}), 404
        
        lines = request.args.get('lines', default=100, type=int)
        
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return jsonify({
            "logs": log_lines,
            "total_lines": len(log_lines)
        })
    
    except Exception as e:
        logging.error(f"Error streaming logs for {server_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/download/status', methods=['GET'])
def get_download_status():
    with download_lock:
        return jsonify(download_status)

@app.route('/api/download', methods=['POST'])
def download_files():
    try:
        data = request.get_json()
        force = data.get('force', False)
        selected = data.get('selected', None)
        
        def download_thread():
            downloader = Downloader(base_dir, force_download=force)
            downloader.download_services(selected)
        
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()
        
        return jsonify({"message": "Download started"})
    
    except Exception as e:
        logging.error(f"Error starting download: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/download/all', methods=['POST'])
def download_all():
    try:
        data = request.get_json()
        force = data.get('force', False)
        
        def download_thread():
            downloader = Downloader(base_dir, force_download=force)
            downloader.download_services(None)
        
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()
        
        return jsonify({"message": "Download started"})
    
    except Exception as e:
        logging.error(f"Error starting download: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/config/<config_name>', methods=['GET'])
def get_config(config_name):
    try:
        config_paths = {
            'settings.yml': os.path.join(base_dir, 'configuration', 'settings.yml'),
            'velocity.toml': os.path.join(base_dir, 'configuration', 'velocity.toml'),
            'resources.json': os.path.join(base_dir, 'configuration', 'resources.json'),
            'forwarding.secret': os.path.join(base_dir, 'configuration', 'forwarding.secret')
        }
        
        if config_name not in config_paths:
            return jsonify({"error": "Invalid config name"}), 400
        
        config_path = config_paths[config_name]
        
        if not os.path.exists(config_path):
            return jsonify({"error": "Config file not found"}), 404
        
        if config_name == 'forwarding.secret':
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            return jsonify({"content": content, "type": "text"})
        
        with open(config_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        if config_name.endswith('.json'):
            content = json.loads(file_content)
            return jsonify({"content": content, "type": "json", "raw": file_content})
        elif config_name.endswith('.toml'):
            content = toml.loads(file_content)
            return jsonify({"content": content, "type": "toml", "raw": file_content})
        elif config_name.endswith('.yml') or config_name.endswith('.yaml'):
            content = yaml.safe_load(file_content)
            return jsonify({"content": content, "type": "yaml", "raw": file_content})
        else:
            return jsonify({"content": file_content, "type": "text"})
    
    except Exception as e:
        logging.error(f"Error reading config {config_name}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/config/<config_name>', methods=['POST'])
def save_config(config_name):
    try:
        config_paths = {
            'settings.yml': os.path.join(base_dir, 'configuration', 'settings.yml'),
            'velocity.toml': os.path.join(base_dir, 'configuration', 'velocity.toml'),
            'resources.json': os.path.join(base_dir, 'configuration', 'resources.json'),
            'forwarding.secret': os.path.join(base_dir, 'configuration', 'forwarding.secret')
        }
        
        if config_name not in config_paths:
            return jsonify({"error": "Invalid config name"}), 400
        
        config_path = config_paths[config_name]
        data = request.get_json()
        content = data.get('content')
        field_path = data.get('field_path')
        
        if content is None:
            return jsonify({"error": "Content is required"}), 400
        
        if config_name == 'forwarding.secret':
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(str(content).strip())
            return jsonify({"message": "Config saved successfully"})
        
        if field_path:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_name.endswith('.json'):
                    config_data = json.load(f)
                elif config_name.endswith('.toml'):
                    config_data = toml.load(f)
                elif config_name.endswith('.yml') or config_name.endswith('.yaml'):
                    config_data = yaml.safe_load(f)
                else:
                    return jsonify({"error": "Field editing not supported for this file type"}), 400
            
            keys = field_path.split('.')
            current = config_data
            for key in keys[:-1]:
                if isinstance(current, dict):
                    current = current[key]
                else:
                    return jsonify({"error": f"Invalid field path: {field_path}"}), 400
            
            if isinstance(current, dict):
                current[keys[-1]] = content
            else:
                return jsonify({"error": f"Invalid field path: {field_path}"}), 400
            
            content = config_data
        
        with open(config_path, 'w', encoding='utf-8') as f:
            if config_name.endswith('.json'):
                json.dump(content, f, indent=2)
            elif config_name.endswith('.toml'):
                toml.dump(content, f)
            elif config_name.endswith('.yml') or config_name.endswith('.yaml'):
                yaml.dump(content, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            else:
                f.write(str(content))
        
        return jsonify({"message": "Config saved successfully"})
    
    except Exception as e:
        logging.error(f"Error saving config {config_name}: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    atexit.register(process_manager.cleanup)
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)

