import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import root_mean_squared_error, mean_absolute_error
from pmdarima import auto_arima
import traceback

def evaluate_models(ts, steps=1260, lags=10):
    if len(ts.shape) > 1:
        ts = ts.ravel()
    diff_ts = np.diff(ts)
    X, y = [], []
    for i in range(lags, len(diff_ts)):
        X.append(diff_ts[i-lags:i])
        y.append(diff_ts[i])
    X, y = np.array(X), np.array(y)

    split_idx = int(len(ts) * 0.8)
    ts_train, ts_test = ts[:split_idx], ts[split_idx:]

    ml_split = split_idx - lags - 1
    if ml_split < 0: ml_split = int(len(X)*0.8)
    X_train, y_train = X[:ml_split], y[:ml_split]
    X_test, y_test = X[ml_split:], y[ml_split:]

    models = {
        "RandomForest": RandomForestRegressor(n_estimators=50, random_state=42),
        "GradientBoosting": GradientBoostingRegressor(n_estimators=50, random_state=42),
        "LinearRegression": LinearRegression()
    }

    best_name = None
    best_rmse = np.inf
    best_mae = np.inf
    best_model = None

    for name, m in models.items():
        try:
            m.fit(X_train, y_train)
            preds_diff = m.predict(X_test)
            reconstructed = [ts_train[-1]]
            for d in preds_diff:
                reconstructed.append(reconstructed[-1] + d)
            rmse = root_mean_squared_error(ts_test[:len(preds_diff)], reconstructed[1:len(preds_diff)+1])
            if rmse < best_rmse:
                best_rmse = rmse
                best_mae = mean_absolute_error(ts_test[:len(preds_diff)], reconstructed[1:len(preds_diff)+1])
                best_name = name
                best_model = m
        except Exception as e:
            print(f"Error evaluating {name}: {e}")

    try:
        arima_model = auto_arima(ts_train, seasonal=False, suppress_warnings=True, trend='c')
        arima_preds = arima_model.predict(n_periods=len(ts_test))
        arima_rmse = root_mean_squared_error(ts_test, arima_preds)
        if arima_rmse < best_rmse:
            best_rmse = arima_rmse
            best_mae = mean_absolute_error(ts_test, arima_preds)
            best_name = "AutoARIMA"
    except Exception as e:
        print(f"Error evaluating AutoARIMA: {e}")

    if best_name == "AutoARIMA":
        model = auto_arima(ts, seasonal=False, suppress_warnings=True, trend='c')
        in_sample = model.predict_in_sample()
        rmse = root_mean_squared_error(ts[1:], in_sample[1:])
        mae = mean_absolute_error(ts[1:], in_sample[1:])

        # Add random walk noise to arima trajectory to make it look realistic
        f_mean = model.predict(n_periods=steps)
        resids = model.resid()
        noise = np.random.choice(resids, size=steps)
        f_simulated = f_mean + noise

        return f_simulated, best_name, rmse, mae
    else:
        best_model.fit(X, y)
        fitted = best_model.predict(X)
        resids = y - fitted

        forecast_diffs = []
        curr_lags = diff_ts[-lags:].tolist()
        noise_std = np.std(resids)

        for _ in range(steps):
            pred_diff = best_model.predict([curr_lags])[0]
            pred_diff += np.random.normal(0, noise_std)
            forecast_diffs.append(pred_diff)
            curr_lags.append(pred_diff)
            curr_lags.pop(0)

        forecast = [ts[-1]]
        for d in forecast_diffs:
            forecast.append(forecast[-1] + d)

        rmse = root_mean_squared_error(diff_ts[lags:], fitted) # In-sample proxy for diffs
        mae = mean_absolute_error(diff_ts[lags:], fitted)
        return np.array(forecast[1:]), best_name, rmse, mae

data = yf.download('COP=X', period='5y', progress=False)['Close'].dropna().values
fcast, b_name, b_rmse, b_mae = evaluate_models(data)
print("Best:", b_name, "RMSE:", b_rmse)
print("Fcast len:", len(fcast))
plt.plot(data, label='Hist')
plt.plot(range(len(data), len(data)+len(fcast)), fcast, label='Proj')
plt.title(f'Best model: {b_name}')
plt.savefig('test_plot.png')
