import numpy as np
import pandas as pd
from datetime import datetime

from database import get_price_history, save_prediction, get_latest_prediction

def generate_price_forecast(product_id):
    """
    Analyzes historical prices and generates a forecast.
    Saves and returns the forecast dictionary.
    Returns None if insufficient data (fewer than 5 records).
    """
    history = get_price_history(product_id)
    
    if not history or len(history) < 5:
        return None
        
    df = pd.DataFrame([dict(row) for row in history])
    df['checked_at'] = pd.to_datetime(df['checked_at'], format='mixed', errors='coerce')
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df = df.dropna(subset=['checked_at', 'price'])
    
    if len(df) < 5:
        return None
        
    prices = df['price'].values
    current_price = prices[-1]
    
    # Basic statistics
    avg_price = df['price'].mean()
    min_price = df['price'].min()
    max_price = df['price'].max()
    
    # Find price drops (discounts)
    drops = []
    days_between = []
    last_drop_date = None
    
    for i in range(1, len(df)):
        prev = prices[i-1]
        curr = prices[i]
        if curr < prev:
            drop_pct = (prev - curr) / prev * 100
            if drop_pct >= 1.5:  # Minimum 1.5% drop to be considered a discount event
                drops.append(drop_pct)
                drop_date = df.iloc[i]['checked_at']
                if last_drop_date is not None:
                    days_between.append((drop_date - last_drop_date).days)
                last_drop_date = drop_date
                
    decrease_probability = 0.0
    expected_discount = 0.0
    forecast_days = 14
    confidence = "Low"
    
    predicted_low = current_price
    predicted_high = current_price
    
    # Basic prediction for 5-9 records
    if len(df) >= 5 and len(df) < 10:
        confidence = "Low"
        # Calculate basic trend
        trend = np.polyfit(range(len(prices)), prices, 1)[0]
        if trend < -0.01:
            decrease_probability = 0.55
            expected_discount = 3.0
            predicted_low = current_price * 0.95
            predicted_high = current_price * 0.98
        else:
            decrease_probability = 0.20
            
    # Full prediction for 10+ records
    elif len(df) >= 10:
        confidence = "Medium" if len(df) < 30 else "High"
        
        if len(drops) > 0:
            expected_discount = np.mean(drops)
            
            if len(days_between) > 0:
                avg_days = np.mean(days_between)
                if avg_days > 0:
                    forecast_days = max(7, int(avg_days))
            
            # Baseline probability based on frequency
            drop_freq = len(drops) / len(df)
            decrease_probability += drop_freq * 0.5
            
            # Adjust based on current vs average
            if current_price > avg_price:
                decrease_probability += 0.2
            elif current_price <= min_price * 1.02:
                # Almost at lowest, unlikely to drop further
                decrease_probability -= 0.3
                
            # Adjust based on time since last drop
            if last_drop_date is not None:
                days_since_drop = (datetime.now() - last_drop_date).days
                if len(days_between) > 0 and days_since_drop >= np.mean(days_between):
                    decrease_probability += 0.3
            
            # Ensure probability is within reasonable bounds
            decrease_probability = max(0.05, min(0.95, decrease_probability))
            
            # Predict range based on expected discount and volatility
            if decrease_probability > 0.4:
                predicted_low = current_price * (1 - (expected_discount / 100) * 1.2)
                predicted_high = current_price * (1 - (expected_discount / 100) * 0.8)
                # Ensure the predicted range isn't lower than historical min unless downward trend is strong
                if predicted_low < min_price * 0.9:
                    predicted_low = min_price * 0.95
            else:
                predicted_low = current_price
                predicted_high = current_price
        else:
            # No historical discounts
            decrease_probability = 0.1
            expected_discount = 0.0
            predicted_low = current_price
            predicted_high = current_price
            
    predicted_low = round(predicted_low, 2)
    predicted_high = round(predicted_high, 2)
    expected_discount = round(expected_discount, 2)
    decrease_probability = round(decrease_probability, 2)
    
    # Generate explanation
    reasons = []
    if len(drops) > 0:
        reasons.append(f"Product has historically dropped {len(drops)} times in {len(df)} checks.")
        reasons.append(f"Average discount size is {expected_discount}%.")
    if current_price > avg_price:
        reasons.append("Current price is above historical average.")
    elif current_price <= min_price * 1.02:
        reasons.append("Current price is near its historical minimum.")
    
    if len(days_between) > 0:
        avg_days = int(np.mean(days_between))
        if last_drop_date:
            days_since = (datetime.now() - last_drop_date).days
            if days_since >= avg_days:
                reasons.append(f"It has been {days_since} days since last drop (avg is {avg_days}).")
                
    explanation = " ".join(reasons)
    if not explanation:
        explanation = "Prediction is based on basic linear trend analysis."
        
    status = "🔮 Possible price decrease" if decrease_probability > 0.4 else "➡️ Price stable/increasing"
    
    # Save the generated prediction
    save_prediction(
        product_id=product_id,
        predicted_price_low=predicted_low,
        predicted_price_high=predicted_high,
        decrease_probability=decrease_probability,
        expected_discount_percent=expected_discount,
        forecast_days=forecast_days,
        confidence=confidence,
        current_price=current_price,
        explanation=explanation,
        status=status
    )
    
    return {
        "predicted_price_low": predicted_low,
        "predicted_price_high": predicted_high,
        "decrease_probability": decrease_probability,
        "expected_discount_percent": expected_discount,
        "forecast_days": forecast_days,
        "confidence": confidence,
        "historical_avg": avg_price,
        "historical_min": min_price,
        "historical_max": max_price,
        "current_price": current_price,
        "explanation": explanation,
        "status": status,
        "historical_observations": len(df),
        "historical_drops": len(drops)
    }
