import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

os.makedirs("demo_frames_hd", exist_ok=True)
os.makedirs("demo_frames_hd/scroll", exist_ok=True)

options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")
driver = webdriver.Chrome(options=options)

try:
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "width": 1920,
        "height": 1080,
        "deviceScaleFactor": 1,
        "mobile": False
    })
    driver.get("http://localhost:5173")
    time.sleep(2)

    # 1. Switch to REAL DATA mode
    real_btn = driver.find_element(By.XPATH, "//button[contains(., 'REAL DATA') or contains(., 'LOAD REAL DATA')]")
    real_btn.click()
    print("Waiting for REAL DATA mode...")
    WebDriverWait(driver, 15).until(lambda d: "REAL OSM" in d.find_element(By.CLASS_NAME, "data-mode-badge").text or "PARTIAL" in d.find_element(By.CLASS_NAME, "data-mode-badge").text)
    time.sleep(2.5)

    # State 1: Overview with B006 baseline
    driver.save_screenshot("demo_frames_hd/01_real_overview.png")
    print("Saved 01_real_overview.png (1920x1080)")

    # Run simulation
    sim_btn = driver.find_element(By.CLASS_NAME, "demo-sim-btn")
    sim_btn.click()
    time.sleep(0.5)
    driver.save_screenshot("demo_frames_hd/02_sim_phase1.png")
    print("Saved 02_sim_phase1.png")

    time.sleep(1.4)
    driver.save_screenshot("demo_frames_hd/03_sim_phase2.png")
    print("Saved 03_sim_phase2.png")

    time.sleep(1.4)
    driver.save_screenshot("demo_frames_hd/04_sim_phase3_rerouted.png")
    print("Saved 04_sim_phase3_rerouted.png")

    # Capture right panel scroll frames
    right_panel = driver.find_element(By.CLASS_NAME, "right-panel")
    for s in range(0, 451, 45):
        driver.execute_script(f"arguments[0].scrollTop = {s};", right_panel)
        time.sleep(0.12)
        driver.save_screenshot(f"demo_frames_hd/scroll/scroll_{s:03d}.png")
        print(f"Saved scroll_{s:03d}.png")

    # Final overview
    driver.execute_script("arguments[0].scrollTop = 0;", right_panel)
    time.sleep(0.3)
    driver.save_screenshot("demo_frames_hd/05_final_overview.png")
    print("Saved 05_final_overview.png")

finally:
    driver.quit()
print("All HD frames captured successfully!")
