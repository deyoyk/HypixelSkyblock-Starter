import os
import sys
import time
import subprocess
import logging
import platform
import signal
import atexit
import shutil
import urllib.request
from enum import Enum


LOG_FILE = "starter.log"


class ServiceType(Enum):
    API = "ServiceAPI.jar"
    AUCTION_HOUSE = "ServiceAuctionHouse.jar"
    BAZAAR = "ServiceBazaar.jar"
    DARK_AUCTION = "ServiceDarkAuction.jar"
    DATA_MUTEX = "ServiceDataMutex.jar"
    FRIEND = "ServiceFriend.jar"
    ITEM_TRACKER = "ServiceItemTracker.jar"
    ORCHESTRATOR = "ServiceOrchestrator.jar"
    PARTY = "ServiceParty.jar"


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
    (0, "PROTOTYPE_LOBBY"),
    (0, "BEDWARS_LOBBY"),
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
        
        if os.path.exists(download_path) and not self.force_download:
            logging.info(f"Exists in downloads: {download_path}")
        else:
            os.makedirs(self.downloads_dir, exist_ok=True)
            logging.info(f"Downloading {url} to {download_path}")
            urllib.request.urlretrieve(url, download_path)
        

        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path) or self.force_download:
            shutil.copy2(download_path, path)
            logging.info(f"Copied {download_path} -> {path}")

    def download_all(self):
        for s in ServiceType:
            self.fetch(
                f"{self.release_base}/{s.value}",
                os.path.join(self.services_dir, s.value),
            )

        self.fetch(
            "https://github.com/Swofty-Developments/HypixelSkyBlock/releases/download/latest/SkyBlockProxy.jar",
            os.path.join(self.config_dir, "SkyBlockProxy.jar"),
        )
        

        self.fetch(
            f"{self.release_base}/HypixelCore.jar",
            os.path.join(self.services_dir, "HypixelCore.jar"),
        )


class FileManager:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.config_dir = os.path.join(base_dir, "configuration")
        self.proxy_dir = os.path.join(base_dir, "proxy")
        self.gameserver_dir = os.path.join(base_dir, "gameserver")
        self.limbo_dir = os.path.join(base_dir, "limbo")
        self.services_dir = os.path.join(base_dir, "services")
        self.logs_dir = os.path.join(base_dir, "logs")

    def copy_file(self, src, dst):
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            logging.info(f"Copied {src} -> {dst}")

    def setup_directories(self, skip_jar_copy=False):
        os.makedirs(self.proxy_dir, exist_ok=True)
        os.makedirs(os.path.join(self.proxy_dir, "plugins"), exist_ok=True)
        os.makedirs(os.path.join(self.proxy_dir, "configuration"), exist_ok=True)
        os.makedirs(self.gameserver_dir, exist_ok=True)
        os.makedirs(os.path.join(self.gameserver_dir, "configuration"), exist_ok=True)
        os.makedirs(self.limbo_dir, exist_ok=True)
        os.makedirs(self.services_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)


        if not skip_jar_copy:
            proxy_jar_path = os.path.join(self.config_dir, "velocity.jar")
            if os.path.exists(proxy_jar_path):
                self.copy_file(
                    os.path.join(self.config_dir, "velocity.jar"),
                    os.path.join(self.proxy_dir, "velocity.jar")
                )
        self.copy_file_if_not_exists(
            os.path.join(self.config_dir, "velocity.toml"),
            os.path.join(self.proxy_dir, "velocity.toml")
        )
        self.copy_file_if_not_exists(
            os.path.join(self.config_dir, "resources.json"),
            os.path.join(self.proxy_dir, "configuration", "resources.json")
        )
        
        if not skip_jar_copy:
            limbo_jar_path = os.path.join(self.config_dir, "NanoLimbo.jar")
            if os.path.exists(limbo_jar_path):
                self.copy_file(
                    os.path.join(self.config_dir, "NanoLimbo.jar"),
                    os.path.join(self.limbo_dir, "NanoLimbo.jar")
                )
        
        proxy_plugin_path = os.path.join(self.config_dir, "SkyBlockProxy.jar")
        if os.path.exists(proxy_plugin_path):
            self.copy_file(
                os.path.join(self.config_dir, "SkyBlockProxy.jar"),
                os.path.join(self.proxy_dir, "plugins", "SkyBlockProxy.jar")
            )

        self.copy_file_if_not_exists(
            os.path.join(self.config_dir, "forwarding.secret"),
            os.path.join(self.proxy_dir, "forwarding.secret")
        )
        

        self.copy_file_if_not_exists(
            os.path.join(self.config_dir, "settings.yml"),
            os.path.join(self.limbo_dir, "settings.yml")
        )

        if os.path.exists(self.config_dir):
            for item in os.listdir(self.config_dir):
                if item == "resources.json":
                    continue
                
                src_path = os.path.join(self.config_dir, item)
                dst_path = os.path.join(self.gameserver_dir, "configuration", item)
                
                if os.path.isdir(src_path):
                    if not os.path.exists(dst_path):
                        shutil.copytree(src_path, dst_path)
                        logging.info(f"Copied dir {src_path} -> {dst_path}")
                else:
                    _, ext = os.path.splitext(item)
                    if ext not in ['.jar', '.toml', '.yml'] and not item.endswith('.secret'):
                        if not os.path.exists(dst_path):
                            shutil.copy2(src_path, dst_path)
                            logging.info(f"Copied {src_path} -> {dst_path}")
        
        core_jar_path = os.path.join(self.services_dir, "HypixelCore.jar")
        if os.path.exists(core_jar_path):
            gameserver_core_path = os.path.join(self.gameserver_dir, "HypixelCore.jar")
            if not os.path.exists(gameserver_core_path):
                shutil.copy2(core_jar_path, gameserver_core_path)
                logging.info(f"Copied {core_jar_path} -> {gameserver_core_path}")
        
        
        self.copy_file_if_not_exists(
            os.path.join(self.config_dir, "resources.json"),
            os.path.join(self.services_dir, "configuration", "resources.json")
        )
        self.copy_file_if_not_exists(
            os.path.join(self.config_dir, "resources.json"),
            os.path.join(self.gameserver_dir, "configuration", "resources.json")
        )

    def copy_file_if_not_exists(self, src, dst):
        if not os.path.exists(dst) and os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            logging.info(f"Copied {src} -> {dst}")

    def copy_forwarding_and_resources(self):
        self.copy_file(
            os.path.join(self.config_dir, "forwarding.secret"),
            os.path.join(self.proxy_dir, "forwarding.secret")
        )
        self.copy_file(
            os.path.join(self.config_dir, "resources.json"),
            os.path.join(self.proxy_dir, "configuration", "resources.json")
        )
        self.copy_file(
            os.path.join(self.config_dir, "resources.json"),
            os.path.join(self.services_dir, "configuration", "resources.json")
        )
        self.copy_file(
            os.path.join(self.config_dir, "resources.json"),
            os.path.join(self.gameserver_dir, "configuration", "resources.json")
        )


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

    def start_services(self):
        for s in ServiceType:
            jar = os.path.join(self.services_dir, s.value)
            if not os.path.isfile(jar):
                logging.warning(f"{s.value} missing")
                continue
            log = open(os.path.join(self.logs_dir, f"{s.value.replace('.jar', '.log')}"), "a")
            p = subprocess.Popen(
                ["java", "-Xms256M", "-Xmx512M", "-jar", s.value],
                cwd=self.services_dir,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            self.proc_mgr.add(p, s.value)
            time.sleep(1)

    def start_servers(self):
        for enabled, server in ALL_SERVER_TYPES:
            for i in range(enabled):
                if server == "PROTOTYPE_LOBBY":
                    core = os.path.join(self.gameserver_dir, "HypixelCore.jar")
                    if not os.path.isfile(core):
                        logging.warning(f"HypixelCore.jar missing for {server}")
                        continue
                    log = open(os.path.join(self.logs_dir, f"{server}_{i}.log"), "a")
                    p = subprocess.Popen(
                        ["java", "-Xms1G", "-Xmx2G", "-jar", "HypixelCore.jar", server],
                        cwd=self.gameserver_dir,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                    )
                    self.proc_mgr.add(p, f"{server}_{i}")
                    time.sleep(5)  
        
        for enabled, server in ALL_SERVER_TYPES:
            for i in range(enabled):
                if server != "PROTOTYPE_LOBBY":
                    core = os.path.join(self.gameserver_dir, "HypixelCore.jar")
                    if not os.path.isfile(core):
                        logging.warning(f"HypixelCore.jar missing for {server}")
                        continue
                    log = open(os.path.join(self.logs_dir, f"{server}_{i}.log"), "a")
                    p = subprocess.Popen(
                        ["java", "-Xms1G", "-Xmx2G", "-jar", "HypixelCore.jar", server],
                        cwd=self.gameserver_dir,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                    )
                    self.proc_mgr.add(p, f"{server}_{i}")
                    time.sleep(5)  


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout),
        ],
    )


def get_user_choice():
    print("\n=== Hypixel SkyBlock Orchestrator ===")
    print("1. Download everything (force redownload)")
    print("2. Download only missing files")
    print("3. Just start existing jars")
    print("4. Exit")
    choice = input("Select option [1-4]: ").strip()
    return choice


def main():
    setup_logging()
    logging.info("Orchestrator starting")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(base_dir, "configuration")
    proxy_dir = os.path.join(base_dir, "proxy")
    limbo_dir = os.path.join(base_dir, "limbo")
    services_dir = os.path.join(base_dir, "services")
    gameserver_dir = os.path.join(base_dir, "gameserver")
    logs_dir = os.path.join(base_dir, "logs")


    if os.path.exists(logs_dir):
        shutil.rmtree(logs_dir)
    os.makedirs(logs_dir, exist_ok=True)
    
    os.makedirs(config_dir, exist_ok=True)

    choice = get_user_choice()

    if choice == "4":
        print("Exiting...")
        sys.exit(0)

    force_download = (choice == "1")
    download_only_missing = (choice == "2")
    skip_download = (choice == "3")

    proc_mgr = ProcessManager()
    downloader = Downloader(base_dir, force_download=force_download)
    file_mgr = FileManager(base_dir)
    starter = ServiceStarter(base_dir, config_dir, proxy_dir, limbo_dir, services_dir, gameserver_dir, logs_dir, proc_mgr)

    atexit.register(proc_mgr.cleanup)
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    if skip_download:
        logging.info("Skipping download and directory setup, using existing files")
    else:
        if force_download:
            logging.info("Force redownloading all files")
            shutil.rmtree(services_dir, ignore_errors=True)
            os.makedirs(services_dir, exist_ok=True)
        elif download_only_missing:
            logging.info("Downloading only missing files")

        downloader.download_all()

    file_mgr.setup_directories(skip_jar_copy=skip_download)
    
    if skip_download:
        file_mgr.copy_forwarding_and_resources()
    starter.start_proxy()
    starter.start_nanolimbo()
    starter.start_services()
    starter.start_servers()

    logging.info("Startup complete - keeping process running")

    while True:
        time.sleep(10)


if __name__ == "__main__":
    main()
