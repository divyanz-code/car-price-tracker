import pandas as pd
import datetime
import smtplib
from playwright.sync_api import sync_playwright
from apscheduler.schedulers.blocking import BlockingScheduler

# Define target car websites
CARS = [
    {
        "name": "Hyundai Creta (CarDekho)",
        "url": "https://www.cardekho.com/hyundai/creta",
        "site": "CarDekho",
        "selector": "#rf01 > div.app-content > div > main > div.overviewTop.overviewTopv.bottom > div > div.price",
    },
    {
        "name": "Maruti Swift (CarWale)",
        "url": "https://www.carwale.com/maruti-suzuki-cars/swift/",
        "site": "CarWale",
        "selector": "#root > div:nth-child(2) > div.o-bWHzMb.o-ducbvd.o-cglRxs.YONMcZ.o-fpkJwH.o-dCyDMp > div > section > div.o-ItVGT.o-bIMsfE.o-eFudgX.o-czEIGQ.o-eKWNKE.o-fBNTVC.o-chzWeu.o-cpnuEd.o-bqHweY > div.o-fznVCs.o-cgFpsP.o-fzptZB > div.o-dEJOrr.o-efHQCX.o-biwSqu.o-fznJDS.o-fznJzb.o-bKazct.o-cpnuEd > div:nth-child(1) > span",
    },
]

# Get target price from user
target_price_inputs = {}
for car in CARS:
    while True:
        try:
            target_price = float(input(f"Enter your target price for {car['name']} (in ₹): "))
            target_price_inputs[car['name']] = target_price
            break
        except ValueError:
            print("Please enter a valid number.")

# Function to scrape car prices using Playwright
def get_price(url, selector, site):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_selector(selector, timeout=5000)

            # Extract price
            price_text = page.locator(selector).text_content()
            browser.close()

            # Clean and extract price
            price = "".join(filter(str.isdigit, price_text))  # Keep only numbers
            return int(price) if price.isdigit() else None

    except Exception as e:
        print(f"Error scraping {site}: {e}")
        return None

# Function to track car prices and save to CSV
def track_car_prices():
    print("Fetching latest car prices...")
    data = []
    
    for car in CARS:
        price = get_price(car["url"], car["selector"], car["site"])
        if price:
            data.append({
                "Car Model": car["name"],
                "Price": price,
                "Website": car["site"],
                "Date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

            # Check if the price is within ±25,000 of the user's target price
            target_price = target_price_inputs.get(car["name"])
            if target_price and (target_price - 25000 <= price <= target_price + 25000):
                print(f"🛒 Time to buy {car['name']}! Current Price: ₹{price}, Target Price: ₹{target_price}")

    # Save to CSV
    if data:
        df = pd.DataFrame(data)
        df.to_csv("car_prices.csv", mode="a", header=False, index=False)
        print("Data saved to car_prices.csv")

        # Check price trends
        analyze_price_trend(df)

# Function to analyze price trends & send alerts
def analyze_price_trend(df):
    # Read previous price data
    try:
        prev_df = pd.read_csv("car_prices.csv", names=["Car Model", "Price", "Website", "Date"])
    except FileNotFoundError:
        prev_df = df

    for car in CARS:
        car_data = prev_df[prev_df["Car Model"] == car["name"]]
        
        if len(car_data) > 1:
            latest_price = car_data.iloc[-1]["Price"]
            previous_price = car_data.iloc[-2]["Price"]

            # Check if price is dropping
            if latest_price < previous_price:
                print(f"🔻 Price Drop for {car['name']}! Old: ₹{previous_price}, New: ₹{latest_price}")

                # Check if the price is within ±25,000 of the user's target price
                target_price = target_price_inputs.get(car["name"])
                if target_price and (target_price - 25000 <= latest_price <= target_price + 25000):
                    print(f"🛒 Time to buy {car['name']}! Current Price: ₹{latest_price}, Target Price: ₹{target_price}")

                # Send email alert if price is below target
                if latest_price <= target_price:
                    send_email(car["name"], latest_price, car["site"])

# Function to send email alert
def send_email(car, price, website):
    sender_email = "your_email@gmail.com"
    receiver_email = "recipient_email@gmail.com"
    password = "your_email_password"

    subject = f"🚗 Price Drop Alert! {car} now at ₹{price}"
    body = f"The price of {car} on {website} has dropped to ₹{price}. Check it out here: {CARS[0]['url']}"

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, password)
        message = f"Subject: {subject}\n\n{body}"
        server.sendmail(sender_email, receiver_email, message)
        server.quit()
        print("✅ Email alert sent!")
    except Exception as e:
        print(f"❌ Email sending failed: {e}")

# Scheduler to run tracking every 24 hours
scheduler = BlockingScheduler()
scheduler.add_job(track_car_prices, "interval", hours=24)

if __name__ == "__main__":
    track_car_prices()  # Run once before starting the scheduler
    scheduler.start()
