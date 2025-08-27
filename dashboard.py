import streamlit as st
import pandas as pd
import requests
import joblib
import os
from pathlib import Path
import tempfile

# Google Drive file ID for RF_Deep model
GDRIVE_FILE_ID = "1YTULpDvgtFombMsyUgrdRDuUAoZQGKmE"
MODEL_FILENAME = "rf_deep_model.joblib"

@st.cache_data
def download_model_from_gdrive(file_id, output_path):
    """Download model from Google Drive handling virus scan warning"""
    import re
    
    with st.spinner("🔄 Downloading RF_Deep model from Google Drive..."):
        try:
            session = requests.Session()
            
            # Step 1: Get the initial page with virus warning
            st.write("📄 Getting download page...")
            initial_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            response = session.get(initial_url)
            
            if response.status_code != 200:
                st.error(f"Failed to access Google Drive. Status: {response.status_code}")
                return False
            
            # Step 2: Extract UUID from the virus scan warning page
            st.write("🔍 Extracting download parameters...")
            uuid_match = re.search(r'name="uuid" value="([^"]+)"', response.text)
            
            if not uuid_match:
                st.error("Could not extract download UUID from Google Drive response")
                return False
            
            uuid = uuid_match.group(1)
            st.write(f"✅ Found UUID: {uuid[:8]}...")
            
            # Step 3: Make the actual download request
            st.write("⬇️ Starting model download...")
            download_url = "https://drive.usercontent.google.com/download"
            params = {
                'id': file_id,
                'export': 'download', 
                'confirm': 't',
                'uuid': uuid
            }
            
            download_response = session.get(download_url, params=params, stream=True)
            
            if download_response.status_code != 200:
                st.error(f"Download failed. Status: {download_response.status_code}")
                return False
            
            # Step 4: Download file in chunks with progress
            progress_bar = st.progress(0)
            progress_text = st.empty()
            
            total_size = int(download_response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(output_path, 'wb') as f:
                for chunk in download_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            progress = downloaded_size / total_size
                            progress_bar.progress(progress)
                            progress_text.text(f"Downloaded: {downloaded_size/(1024*1024):.1f} MB / {total_size/(1024*1024):.1f} MB")
                        else:
                            progress_text.text(f"Downloaded: {downloaded_size/(1024*1024):.1f} MB")
            
            # Step 5: Validate the downloaded file
            st.write("✅ Download complete! Validating model...")
            
            try:
                import joblib
                test_model = joblib.load(output_path)
                st.success(f"🎉 Model validated successfully! Type: {type(test_model).__name__}")
                return True
                
            except Exception as e:
                st.error(f"Downloaded file is not a valid model: {str(e)}")
                if os.path.exists(output_path):
                    os.remove(output_path)
                return False
                
        except Exception as e:
            st.error(f"Download failed: {str(e)}")
            return False

@st.cache_resource
def load_rf_deep_model():
    """Load RF_Deep model, downloading from Google Drive if necessary"""
    
    # Check if model exists locally first
    local_model_path = "./models/rf_deep_model.joblib"
    temp_model_path = os.path.join(tempfile.gettempdir(), MODEL_FILENAME)
    
    model_path = None
    
    # Try local path first
    if os.path.exists(local_model_path):
        model_path = local_model_path
        st.success("Using local RF_Deep model")
    
    # Try temp directory
    elif os.path.exists(temp_model_path):
        model_path = temp_model_path
        st.info("Using previously downloaded RF_Deep model")
    
    # Download from Google Drive
    else:
        st.info("Downloading RF_Deep model from Google Drive...")
        if download_model_from_gdrive(GDRIVE_FILE_ID, temp_model_path):
            model_path = temp_model_path
            st.success("RF_Deep model downloaded successfully!")
        else:
            st.error("Failed to download model from Google Drive")
            return None
    
    # Load the model
    try:
        model = joblib.load(model_path)
        return model
    except Exception as e:
        st.error(f"Error loading model: {str(e)}")
        return None

def main():
    st.set_page_config(
        page_title="NCAA Predictions - Cloud Dashboard",
        page_icon="🏈",
        layout="wide"
    )
    
    st.title("🏈 NCAA Football Predictions - Cloud Dashboard")
    st.write("This dashboard uses the RF_Deep model downloaded from Google Drive")
    
    # Load the model
    model = load_rf_deep_model()
    
    if model is None:
        st.error("Could not load RF_Deep model. Please check the Google Drive link.")
        st.stop()
    
    st.success("✅ RF_Deep model loaded successfully!")
    st.write(f"Model type: {type(model).__name__}")
    
    # Display model info if available
    if hasattr(model, 'feature_importances_'):
        st.subheader("Model Information")
        st.write(f"Number of features: {len(model.feature_importances_)}")
        
        # Show top feature importances
        if len(model.feature_importances_) > 0:
            st.subheader("Top Feature Importances")
            
            # Create feature names (we don't know the actual names without the training data)
            feature_names = [f"Feature_{i+1}" for i in range(len(model.feature_importances_))]
            
            # Create DataFrame for feature importances
            importance_df = pd.DataFrame({
                'Feature': feature_names,
                'Importance': model.feature_importances_
            }).sort_values('Importance', ascending=False)
            
            # Display top 10 features
            st.dataframe(importance_df.head(10))
            
            # Plot feature importances
            st.bar_chart(importance_df.head(10).set_index('Feature')['Importance'])
    
    # Add prediction interface
    st.subheader("Model Prediction Interface")
    st.write("Model is ready for predictions!")
    st.info("To add prediction functionality, you would need to:")
    st.write("1. Define the expected input features")
    st.write("2. Create input widgets for each feature") 
    st.write("3. Call model.predict() with the input data")
    st.write("4. Display the prediction results")
    
    # Display model attributes
    with st.expander("Model Technical Details"):
        st.write("**Model Attributes:**")
        for attr in dir(model):
            if not attr.startswith('_') and not callable(getattr(model, attr)):
                try:
                    value = getattr(model, attr)
                    if hasattr(value, 'shape'):
                        st.write(f"- {attr}: {type(value).__name__} with shape {value.shape}")
                    else:
                        st.write(f"- {attr}: {value}")
                except:
                    st.write(f"- {attr}: {type(getattr(model, attr)).__name__}")

if __name__ == "__main__":
    main()