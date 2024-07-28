from selenium import webdriver
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
#chrome_options.add_argument('--headless')  # Add this line for headless mode


def retrieve_webpage(url):

  driver = webdriver.Chrome(options=chrome_options)
  driver.get(url)
  driver.implicitly_wait(2)
  page_source = driver.page_source
  return (page_source)


print(retrieve_webpage("https://hypixel.net"))