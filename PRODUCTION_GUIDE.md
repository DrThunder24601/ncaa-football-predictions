# NCAA Football Predictions - Production Guide

## 🏈 Quick Start (Daily Operations)

### Run Daily Predictions
```bash
# Windows: Double-click or run from command line
run_workflow.bat daily

# Or direct Python call
python daily_workflow.py --mode daily
```

### Launch Dashboard
```bash
# Windows: Double-click or run from command line
launch_dashboard.bat

# Opens at: http://localhost:8501
```

---

## 🎯 Production System Overview

### **Proven Performance**
- **Model:** 4-Feature Linear Regression
- **Test MAE:** 1.5 points (excellent for college football)
- **Features:** Offensive efficiency, Defensive efficiency, Home favorite, Vegas line
- **Training Data:** 2024 season statistics

### **Production Data Flow**
```
CFBD API → Team Stats → Feature Engineering → Linear Model → 
Google Sheets → Dashboard Visualization
```

---

## 📁 Production Scripts (Core System)

### **Daily Automation**
| File | Purpose | Usage |
|------|---------|-------|
| `run_workflow.bat` | **Main entry point** | Daily automation runner |
| `daily_workflow.py` | **Core workflow** | Data update → predictions → output |
| `sunday_workflow.py` | **Weekly analysis** | Performance tracking + predictions |

### **Prediction Engine**
| File | Purpose | Usage |
|------|---------|-------|
| `src/prediction/football_automation.py` | **Main prediction logic** | Model loading, feature engineering, predictions |
| `src/prediction/comprehensive_feature_engineering.py` | **Feature creation** | Advanced feature engineering (if needed) |
| `src/prediction/results_tracker.py` | **Performance tracking** | Track prediction accuracy |

### **User Interface**
| File | Purpose | Usage |
|------|---------|-------|
| `launch_dashboard.bat` | **Dashboard launcher** | Start Streamlit web interface |
| `dashboard.py` | **Main dashboard** | Streamlit web interface |
| `quick_dashboard.py` | **Simple dashboard** | Lightweight version |

### **Data Processing**
| File | Purpose | Usage |
|------|---------|-------|
| `src/data_processing/ncaaf_pipeline.py` | **Data pipeline** | Full data processing workflow |
| `src/modeling/ncaaf_model_check.py` | **Model validation** | Load and evaluate models |
| `src/analysis/ncaaf_confidence_analysis.py` | **Confidence analysis** | Prediction confidence intervals |

---

## 🧪 Experimental/Development Scripts

### **Model Training & Research**
| File | Status | Notes |
|------|--------|-------|
| `train_linear_model.py` | ✅ **Successful** | Created winning 4-feature model |
| `train_simple_linear.py` | ✅ **Successful** | Alternative linear training approach |
| `train_rf_7_features.py` | ❌ **Poor performance** | 12.16 MAE - not recommended |
| `train_enhanced_random_forest.py` | ❌ **Problematic** | Complex model with issues |
| `train_production_random_forest.py` | ⚠️ **Backup model** | Fallback if linear fails |

### **Model Comparison & Analysis**
| File | Status | Notes |
|------|--------|-------|
| `compare_models.py` | 📊 **Analysis** | RF vs Linear comparison |
| `compare_all_algorithms.py` | 📊 **Analysis** | Multi-model comparison |
| `compare_enhanced_models.py` | 📊 **Analysis** | Enhanced model evaluation |
| `compare_7f_vs_4f.py` | 📊 **Analysis** | 7-feature vs 4-feature comparison |

### **Testing & Debugging**
| File | Status | Notes |
|------|--------|-------|
| `test_*.py` | 🧪 **Development** | Various testing scripts |
| `debug_*.py` | 🐛 **Debugging** | Troubleshooting scripts |
| `diagnose_*.py` | 🔍 **Analysis** | Model diagnostic scripts |

### **Data Analysis & Utilities**
| File | Status | Notes |
|------|--------|-------|
| `analyze_*.py` | 📊 **Research** | Data analysis scripts |
| `create_*.py` | 🔧 **Utilities** | Data creation/mapping scripts |
| `fix_*.py` | 🔧 **Utilities** | Bug fix scripts |

---

## 📊 Production Model Files

### **Primary Model (In Use)**
```
models/
├── linear_regression_model.joblib     ← MAIN PRODUCTION MODEL (1.5 MAE)
├── features.txt                       ← 4 features used by production model
└── [training_metrics files]           ← Performance documentation
```

### **Backup Models**
```
models/
├── random_forest_model.joblib         ← Fallback RF model (4 features)
├── rf_features.txt                    ← RF feature list
└── [other model files]                ← Research/experimental models
```

### **Avoid in Production**
- `rf_7_feature_model.joblib` - Poor performance (12.16 MAE)
- `enhanced_random_forest_model.joblib` - Overly complex, compatibility issues

---

## 🔧 Configuration Files

### **Core Configuration**
| File | Purpose |
|------|---------|
| `cfbdata_to_espn_comprehensive_mapping.csv` | Team name mappings |
| `vegas_name_variations.csv` | Vegas line team name mappings |
| `config/` | Configuration directory |

### **External Dependencies**
- **Google Sheets API:** Service account JSON file
- **CFBD API Key:** Hardcoded in football_automation.py
- **Odds API Key:** For Vegas line integration

---

## 📈 Performance Metrics

### **Model Comparison Results**
| Model | Features | Test MAE | Status |
|-------|----------|----------|--------|
| **Linear Regression** | **4** | **1.5 points** | **🏆 PRODUCTION** |
| Random Forest (4-feature) | 4 | ~3-5 points | 🔄 Backup |
| Random Forest (7-feature) | 7 | 12.16 points | ❌ Avoid |
| Enhanced Random Forest | 200+ | Variable | ❌ Problematic |

### **Why Linear Regression Wins:**
- Simplicity prevents overfitting
- Focused on most predictive features
- Excellent generalization (1.5 MAE)
- Reliable and consistent predictions

---

## 🚀 Deployment Notes

### **Daily Workflow Modes**
```bash
python daily_workflow.py --mode daily      # Standard daily run
python daily_workflow.py --mode pipeline   # Full data pipeline
python daily_workflow.py --mode analysis   # Analysis only
python daily_workflow.py --mode status     # Status check
```

### **Google Sheets Integration**
- **Predictions Tab:** Main model output
- **ESPN Schedule Pull Tab:** Game schedule data
- **Auto-updates:** Via Google Sheets API

### **Dashboard Features**
- Real-time prediction display
- Model performance metrics
- Prediction confidence intervals
- Vegas line comparison
- Betting edge identification

---

## 📝 Development History

This project evolved through extensive experimentation:

1. **Started with complex models** - Enhanced Random Forest with 200+ features
2. **Discovered simplicity wins** - 4-feature approach outperformed complex models
3. **Linear regression emerged as winner** - Best performance with lowest complexity
4. **Production system stabilized** - Focused on proven 1.5 MAE linear model

The "experimental" scripts document this learning journey and remain for reference, debugging, and future research.

---

## 🎯 Recommendations

### **For Daily Use:**
1. Use `run_workflow.bat` for daily predictions
2. Use `launch_dashboard.bat` for visualization
3. Monitor prediction accuracy via dashboard
4. Check logs in `logs/` directory for issues

### **For Development:**
1. All model training scripts are preserved for research
2. Comparison scripts help evaluate new approaches
3. Test scripts ensure system reliability
4. Debug scripts help troubleshoot issues

### **Best Practices:**
- Stick with the proven 4-feature linear model
- Run daily workflow consistently for fresh predictions
- Use dashboard for decision making
- Archive logs periodically

---

**Last Updated:** August 2025  
**Model Version:** 4-Feature Linear Regression (1.5 MAE)  
**Status:** Production Ready ✅