import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

os.makedirs("demo_frames", exist_ok=True)

options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")
driver = webdriver.Chrome(options=options)

try:
    driver.get("http://localhost:5173")
    time.sleep(2)

    # 1. Switch to REAL DATA mode
    real_btn = driver.find_element(By.XPATH, "//button[contains(., 'REAL DATA') or contains(., 'LOAD REAL DATA')]")
    real_btn.click()
    print("Waiting for REAL DATA mode...")
    WebDriverWait(driver, 15).until(lambda d: "REAL OSM" in d.find_element(By.CLASS_NAME, "data-mode-badge").text or "PARTIAL" in d.find_element(By.CLASS_NAME, "data-mode-badge").text)
    time.sleep(2)

    # Capture State 1: Overview with B006 selected (baseline)
    driver.save_screenshot("demo_frames/01_real_overview.png")
    print("Captured 01_real_overview.png")

    # Find the positions of key elements for mouse targeting
    sim_btn = driver.find_element(By.CLASS_NAME, "demo-sim-btn")
    print("Sim btn rect:", sim_btn.rect)

    baseline_box = driver.find_element(By.CLASS_NAME, "baseline-box")
    print("Baseline box rect:", baseline_box.rect)

    impact_grid = driver.find_element(By.CLASS_NAME, "story-impact-grid")
    print("Impact grid rect:", impact_grid.rect)

    priority_box = driver.find_element(By.CLASS_NAME, "story-priority-box")
    print("Priority box rect:", priority_box.rect)

    banner = driver.find_element(By.CLASS_NAME, "cyclone-summary-banner")
    print("Banner rect:", banner.rect)

    # Bridge marker location on Leaflet map:
    # Leaflet map container
    map_container = driver.find_element(By.CLASS_NAME, "map-container")
    print("Map container rect:", map_container.rect)

    # 2. Run simulation
    sim_btn.click()
    time.sleep(0.5)
    driver.save_screenshot("demo_frames/02_sim_phase1.png")
    print("Captured 02_sim_phase1.png")

    time.sleep(1.4)
    driver.save_screenshot("demo_frames/03_sim_phase2.png")
    print("Captured 03_sim_phase2.png")

    time.sleep(1.4)
    driver.save_screenshot("demo_frames/04_sim_phase3_rerouted.png")
    print("Captured 04_sim_phase3_rerouted.png")

    # Scroll right panel to view Gemini Brief
    right_panel = driver.find_element(By.CLASS_NAME, "right-panel")
    driver.execute_script("arguments[0].scrollTop = 450;", right_panel)
    time.sleep(0.5)
    driver.save_screenshot("demo_frames/05_gemini_brief.png")
    print("Captured 05_gemini_brief.png")

    driver.execute_script("arguments[0].scrollTop = 0;", right_panel)
    time.sleep(0.5)
    driver.save_screenshot("demo_frames/06_final_overview.png")
    print("Captured 06_final_overview.png")

finally:
    driver.quit()
