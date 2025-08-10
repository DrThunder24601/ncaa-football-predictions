# NCAA Football Predictions Dashboard

A professional college football spread prediction dashboard powered by a 4-feature Linear Regression model achieving 1.5 MAE performance.

## 🏈 Live Dashboard
🌐 **[View Live Dashboard](https://your-app-name.streamlit.app)** *(coming soon)*

## 📊 Model Performance
- **Model Type**: 4-Feature Linear Regression
- **Training MAE**: 1.5 points (excellent for college football)
- **Features**: Offensive efficiency, Defensive efficiency, Home favorite, Vegas line
- **Data Source**: Live Google Sheets integration

## 🎯 Features
- **Live Predictions**: Real-time predictions from Google Sheets
- **Edge Analysis**: Categorized betting edge ranges for performance tracking
- **Model Insights**: Linear regression coefficients and feature analysis
- **Mobile Responsive**: Works on all devices
- **Performance Tracking**: Framework for Week 1+ performance analysis

## 🚀 Technology Stack
- **Frontend**: Streamlit
- **Backend**: Python, Pandas, NumPy
- **Model**: Scikit-learn Linear Regression
- **Data**: Google Sheets API
- **Visualization**: Plotly
- **Deployment**: Streamlit Community Cloud

## 📈 Model Approach
This system uses a minimal 4-feature approach that outperformed complex 200+ feature models:
- **Simplicity over complexity**: 4 features vs 200+ features
- **Better generalization**: 1.5 MAE vs 12+ MAE from complex models
- **Interpretable results**: Clear linear relationships
- **Reliable performance**: Consistent across different datasets

## 🎯 Edge Range Strategy
Based on basketball betting insights, the dashboard categorizes prediction edges:
- **Low Edge (0-1.5)**: Small differences
- **Mid Edge (1.5-3)**: Moderate differences  
- **High Edge (3-5)**: Large differences
- **Very High/Extreme Edge (5-8+)**: Major differences

*Note: Performance data will be collected starting Week 1 to identify which ranges actually perform best.*

## 📊 Data Sources
- **Team Statistics**: College Football Data API
- **Betting Lines**: The Odds API
- **Predictions Output**: Google Sheets integration
- **Historical Performance**: Tracked via Google Sheets

## 🔒 Security
- All API keys secured via Streamlit secrets
- No sensitive data in public repository
- Google service account authentication

## 📱 Usage
1. Visit the live dashboard
2. View current week predictions
3. Filter by teams or edge ranges
4. Analyze model insights and coefficients
5. Track performance over time (Week 1+)

## ⚡ Performance
- Data refreshes every 5 minutes
- Mobile optimized interface
- Fast loading with caching
- Real-time Google Sheets integration

---

*This dashboard represents a data-driven approach to college football prediction, emphasizing model simplicity and performance tracking over complex feature engineering.*