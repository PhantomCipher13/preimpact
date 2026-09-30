import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

options = ChromeOptions()
options.add_argument('--headless=new')
options.add_argument('--window-size=1600,900')
driver = webdriver.Chrome(options=options)

try:
    print('1. Opening http://localhost:5173 ...')
    driver.get('http://localhost:5173')
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'app-layout')))
    time.sleep(1)
    print('PASS: App layout loaded successfully.')

    # Check Demo Mode is active
    badge = driver.find_element(By.CLASS_NAME, 'data-mode-badge').text
    print('Initial data badge:', badge)

    # Check Disruption Card is showing
    card = driver.find_element(By.CLASS_NAME, 'disruption-panel')
    print('Initial Asset ID:', driver.find_element(By.CLASS_NAME, 'story-asset-id').text)
    print('Initial Delta Callout:', driver.find_element(By.CLASS_NAME, 'cd-value').text)

    # Test Cyclone Scenario Floating Drawer
    print('\n2. Testing Cyclone Scenario Drawer...')
    scen_btn = driver.find_element(By.XPATH, "//button[contains(., 'Cyclone Scenario')]")
    scen_btn.click()
    time.sleep(0.5)
    drawer = driver.find_element(By.CLASS_NAME, 'floating-glass-drawer')
    print('Drawer title:', drawer.find_element(By.CLASS_NAME, 'fgd-title').text)
    # Close it
    driver.find_element(By.CLASS_NAME, 'fgd-close').click()
    time.sleep(0.5)
    print('PASS: Cyclone drawer toggled.')

    # Test Graph & POI Floating Drawer
    print('\n3. Testing Graph & POIs Drawer...')
    net_btn = driver.find_element(By.XPATH, "//button[contains(., 'Graph & POIs')]")
    net_btn.click()
    time.sleep(0.5)
    drawer2 = driver.find_element(By.CLASS_NAME, 'floating-glass-drawer')
    print('Drawer title:', drawer2.find_element(By.CLASS_NAME, 'fgd-title').text)
    driver.find_element(By.CLASS_NAME, 'fgd-close').click()
    time.sleep(0.5)
    print('PASS: Graph & POIs drawer toggled.')

    # Test Critical Asset Priorities Tab
    print('\n4. Testing CRITICAL ASSET PRIORITIES Tab...')
    rank_btn = driver.find_element(By.XPATH, "//button[contains(., 'CRITICAL ASSET PRIORITIES')]")
    rank_btn.click()
    time.sleep(0.5)
    modal = driver.find_element(By.CLASS_NAME, 'map-overlay-modal')
    print('Modal title:', modal.find_element(By.CLASS_NAME, 'mom-title').text)
    rank_rows = driver.find_elements(By.CLASS_NAME, 'rank-data')
    print('Ranking rows count:', len(rank_rows))
    # Click return to map
    driver.find_element(By.CLASS_NAME, 'mom-close-btn').click()
    time.sleep(0.5)
    print('PASS: Asset ranking modal opened and returned.')

    # Test Data & Methodology Tab
    print('\n5. Testing DATA & METHODOLOGY Tab...')
    data_btn = driver.find_element(By.XPATH, "//button[contains(., 'DATA & METHODOLOGY')]")
    data_btn.click()
    time.sleep(0.5)
    data_modal = driver.find_element(By.CLASS_NAME, 'map-overlay-modal')
    print('Data modal title:', data_modal.find_element(By.CLASS_NAME, 'mom-title').text)
    driver.find_element(By.CLASS_NAME, 'mom-close-btn').click()
    time.sleep(0.5)
    print('PASS: Data & Methodology modal opened and returned.')

    # Test LOAD REAL DATA mode
    print('\n6. Testing LOAD REAL DATA Mode...')
    real_btn = driver.find_element(By.XPATH, "//button[contains(., 'REAL DATA') or contains(., 'LOAD REAL DATA')]")
    real_btn.click()
    print('Clicked REAL DATA, waiting for API response...')
    WebDriverWait(driver, 15).until(lambda d: 'REAL OSM' in d.find_element(By.CLASS_NAME, 'data-mode-badge').text or 'PARTIAL' in d.find_element(By.CLASS_NAME, 'data-mode-badge').text)
    print('Active mode badge:', driver.find_element(By.CLASS_NAME, 'data-mode-badge').text)
    print('Real Asset ID:', driver.find_element(By.CLASS_NAME, 'story-asset-id').text)
    print('Real Asset Name:', driver.find_element(By.CLASS_NAME, 'story-asset-name').text)
    print('Real Delta:', driver.find_element(By.CLASS_NAME, 'cd-value').text)

    # Test Run Counterfactual Simulation in Real Mode
    print('\n7. Testing RUN COUNTERFACTUAL SIMULATION...')
    sim_btn = driver.find_element(By.CLASS_NAME, 'demo-sim-btn')
    print('Sim button text before click:', sim_btn.text)
    sim_btn.click()
    time.sleep(0.5)
    hud = driver.find_element(By.CLASS_NAME, 'simulation-hud')
    print('Simulation HUD Phase 1:', hud.find_element(By.CLASS_NAME, 'hud-phase-badge').text)
    time.sleep(1.6)
    print('Simulation HUD Phase 2:', hud.find_element(By.CLASS_NAME, 'hud-phase-badge').text)
    time.sleep(1.6)
    print('Simulation HUD Phase 3:', hud.find_element(By.CLASS_NAME, 'hud-phase-badge').text)
    print('PASS: 3-phase simulation animated cleanly.')

    # Test DEMO MODE button
    print('\n8. Switching back to DEMO MODE...')
    demo_btn = driver.find_element(By.XPATH, "//button[contains(., 'DEMO MODE')]")
    demo_btn.click()
    time.sleep(0.5)
    print('Switched back to:', driver.find_element(By.CLASS_NAME, 'data-mode-badge').text)

    # Check for console errors
    logs = driver.get_log('browser')
    errors = [l for l in logs if l['level'] in ['SEVERE', 'ERROR'] and 'favicon.ico' not in l['message']]
    print('\nBrowser Console Errors (excluding favicon):', len(errors))
    for e in errors:
        print('ERROR:', e['message'])
    if not errors:
        print('PASS: Zero console errors!')

finally:
    driver.quit()
