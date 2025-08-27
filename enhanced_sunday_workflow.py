#!/usr/bin/env python3
"""
Enhanced NCAA Football Sunday Automation Workflow
4-Phase Comprehensive Sunday Rollover System
- Phase 1: Data Collection & Updates (7:00 PM)
- Phase 2: Results & Performance Analysis (7:30 PM)  
- Phase 3: Next Week Preparation (8:00 PM)
- Phase 4: System Validation & Cleanup (8:30 PM)
"""

import os
import sys
import logging
import argparse
import shutil
import glob
from datetime import datetime, timedelta
from pathlib import Path

# Import existing modules
sys.path.append(str(Path(__file__).parent / "src"))
from src.prediction.football_automation import (
    get_current_week, update_stats, pull_schedule, 
    write_schedule_to_sheet, make_predictions
)
from src.prediction.results_tracker import ResultsTracker

# Configuration
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
ARCHIVE_DIR = BASE_DIR / "data" / "archive"
LOGS_DIR.mkdir(exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)

# Data retention settings
WEEKS_TO_KEEP = 10  # Keep last 10 weeks of data
MAX_LOG_FILES = 50  # Keep last 50 log files

def setup_logging():
    """Setup comprehensive logging for enhanced Sunday workflow"""
    log_file = LOGS_DIR / f"enhanced_sunday_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def retry_with_backoff(func, max_attempts=3, backoff_seconds=30):
    """Retry function with exponential backoff"""
    for attempt in range(max_attempts):
        try:
            return func(), True
        except Exception as e:
            if attempt < max_attempts - 1:
                wait_time = backoff_seconds * (2 ** attempt)
                logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                import time
                time.sleep(wait_time)
            else:
                logging.error(f"All {max_attempts} attempts failed: {e}")
                return None, False

# PHASE 1: Data Collection & Updates
def phase1_data_collection(logger):
    """
    Phase 1: Data Collection & Updates (7:00 PM)
    - Run 2025 stats collector
    - Update all CSV files with latest stats
    - Validate data integrity
    """
    logger.info("=" * 60)
    logger.info("PHASE 1: DATA COLLECTION & UPDATES")
    logger.info("=" * 60)
    
    success_count = 0
    total_tasks = 3
    
    # Task 1: Run 2025 stats collector
    logger.info("Task 1/3: Running 2025 stats collector...")
    
    def run_stats_collector():
        # Import and run the 2025 stats collector
        sys.path.append(str(BASE_DIR))
        from automated_2025_stats_collector import update_2025_team_stats
        return update_2025_team_stats()
    
    result, success = retry_with_backoff(run_stats_collector, max_attempts=3)
    if success and result:
        logger.info("✅ 2025 stats collection completed successfully")
        success_count += 1
    else:
        logger.error("❌ 2025 stats collection failed after retries")
    
    # Task 2: Update existing stats through football_automation
    logger.info("Task 2/3: Updating team stats through existing system...")
    
    def run_update_stats():
        return update_stats()
    
    result, success = retry_with_backoff(run_update_stats, max_attempts=3)
    if success:
        logger.info(f"✅ Team stats updated successfully (week {result})")
        success_count += 1
    else:
        logger.error("❌ Team stats update failed after retries")
    
    # Task 3: Validate data integrity
    logger.info("Task 3/3: Validating data integrity...")
    
    def validate_data():
        current_week = get_current_week()
        
        # Check for required files
        required_files = [
            DATA_DIR / f"cfbd_team_stats_2025_week{current_week}.csv",
            DATA_DIR / "cfbd_team_stats_2025_week1.csv"
        ]
        
        missing_files = []
        empty_files = []
        
        for file_path in required_files:
            if not file_path.exists():
                missing_files.append(str(file_path))
            else:
                # Check if file has content (more than just headers)
                try:
                    import pandas as pd
                    df = pd.read_csv(file_path)
                    if len(df) == 0:
                        empty_files.append(str(file_path))
                except Exception as e:
                    logger.warning(f"Could not validate {file_path}: {e}")
        
        if missing_files:
            raise Exception(f"Missing required files: {missing_files}")
        if empty_files:
            raise Exception(f"Empty data files found: {empty_files}")
            
        return True
    
    result, success = retry_with_backoff(validate_data, max_attempts=2)
    if success:
        logger.info("✅ Data integrity validation passed")
        success_count += 1
    else:
        logger.error("❌ Data integrity validation failed")
    
    # Phase 1 Summary
    logger.info(f"\nPHASE 1 SUMMARY: {success_count}/{total_tasks} tasks successful")
    return success_count == total_tasks

# PHASE 2: Results & Performance Analysis
def phase2_results_analysis(logger, week=None):
    """
    Phase 2: Results & Performance Analysis (7:30 PM)
    - Results tracker for completed games
    - Model performance analysis
    - Confidence analysis update
    """
    logger.info("=" * 60)
    logger.info("PHASE 2: RESULTS & PERFORMANCE ANALYSIS")
    logger.info("=" * 60)
    
    success_count = 0
    total_tasks = 3
    
    # Task 1: Results tracking for completed games
    logger.info("Task 1/3: Tracking results for completed games...")
    
    def run_results_tracking():
        tracker = ResultsTracker()
        current_week = get_current_week()
        
        # Check previous week(s) for completed games
        weeks_to_check = [current_week - 1, current_week - 2] if current_week > 1 else [current_week]
        if week:
            weeks_to_check = [week]
            
        total_updated = 0
        for check_week in weeks_to_check:
            if check_week > 0:
                logger.info(f"Checking week {check_week} for completed games...")
                results = tracker.update_results_tracking(check_week)
                if results is not None and not results.empty:
                    total_updated += len(results)
                    
        return total_updated
    
    result, success = retry_with_backoff(run_results_tracking, max_attempts=3)
    if success:
        logger.info(f"✅ Results tracking completed: {result} games updated")
        success_count += 1
    else:
        logger.error("❌ Results tracking failed after retries")
    
    # Task 2: Model performance analysis
    logger.info("Task 2/3: Running model performance analysis...")
    
    def run_model_analysis():
        # Import and run model evaluation
        from src.modeling.ncaaf_model_check import load_model_and_evaluate
        metrics = load_model_and_evaluate()
        return metrics
    
    result, success = retry_with_backoff(run_model_analysis, max_attempts=2)
    if success and result:
        logger.info(f"✅ Model performance analysis completed: {result}")
        success_count += 1
    else:
        logger.error("❌ Model performance analysis failed")
    
    # Task 3: Confidence analysis update
    logger.info("Task 3/3: Updating confidence analysis...")
    
    def run_confidence_analysis():
        try:
            from src.analysis.ncaaf_confidence_analysis import NCAAFConfidenceAnalysis
            analyzer = NCAAFConfidenceAnalysis(base_dir=BASE_DIR)
            confidence_results = analyzer.generate_predictions_with_confidence()
            
            if confidence_results is not None:
                betting_recommendations = analyzer.generate_betting_recommendations(confidence_results)
                confidence_file, betting_file = analyzer.save_results(confidence_results, betting_recommendations)
                return {"confidence_file": confidence_file, "betting_file": betting_file}
            return None
        except ImportError:
            logger.warning("Confidence analysis module not found - skipping")
            return "skipped"
    
    result, success = retry_with_backoff(run_confidence_analysis, max_attempts=2)
    if success:
        if result == "skipped":
            logger.info("ℹ️ Confidence analysis skipped (module not available)")
            success_count += 1  # Count as success since it's optional
        elif result:
            logger.info(f"✅ Confidence analysis completed: {result}")
            success_count += 1
        else:
            logger.error("❌ Confidence analysis returned empty results")
    else:
        logger.error("❌ Confidence analysis failed after retries")
    
    # Phase 2 Summary
    logger.info(f"\nPHASE 2 SUMMARY: {success_count}/{total_tasks} tasks successful")
    return success_count >= 2  # Allow one optional failure

# PHASE 3: Next Week Preparation
def phase3_next_week_preparation(logger):
    """
    Phase 3: Current Week Live Predictions (8:00 PM)
    - Pull current week's schedule (not next week)
    - Generate predictions with confidence for current games
    - Update Google Sheets with current week data
    - Clear dashboard cache
    """
    logger.info("=" * 60)
    logger.info("PHASE 3: CURRENT WEEK LIVE PREDICTIONS")
    logger.info("=" * 60)
    
    success_count = 0
    total_tasks = 4
    
    # Task 1: Pull current week schedule for live predictions
    logger.info("Task 1/4: Pulling current week's schedule...")
    
    def pull_current_schedule():
        current_week = get_current_week()
        logger.info(f"Pulling schedule for week {current_week} (current week)")
        return pull_schedule(current_week)
    
    schedule_result, success = retry_with_backoff(pull_current_schedule, max_attempts=3)
    if success and schedule_result is not None:
        logger.info("✅ Current week's schedule pulled successfully")
        success_count += 1
    else:
        logger.error("❌ Schedule pull failed after retries")
    
    # Task 2: Update Google Sheets with schedule
    logger.info("Task 2/4: Updating Google Sheets with schedule...")
    
    def update_sheets_schedule():
        return write_schedule_to_sheet(schedule_result if schedule_result is not None else [])
    
    result, success = retry_with_backoff(update_sheets_schedule, max_attempts=3)
    if success:
        logger.info("✅ Google Sheets updated with schedule")
        success_count += 1
    else:
        logger.error("❌ Google Sheets schedule update failed after retries")
    
    # Task 3: Generate fresh predictions
    logger.info("Task 3/4: Generating fresh predictions...")
    
    def generate_fresh_predictions():
        return make_predictions()
    
    result, success = retry_with_backoff(generate_fresh_predictions, max_attempts=3)
    if success and result is not None:
        logger.info("✅ Fresh predictions generated successfully")
        success_count += 1
    else:
        logger.error("❌ Prediction generation failed after retries")
    
    # Task 4: Clear dashboard cache (create signal file)
    logger.info("Task 4/4: Signaling dashboard to refresh...")
    
    def create_refresh_signal():
        # Create a refresh signal file that dashboard can monitor
        refresh_signal_file = BASE_DIR / "dashboard_refresh_signal.txt"
        with open(refresh_signal_file, 'w') as f:
            f.write(f"REFRESH_REQUESTED_AT_{datetime.now().isoformat()}")
        return True
    
    result, success = retry_with_backoff(create_refresh_signal, max_attempts=2)
    if success:
        logger.info("✅ Dashboard refresh signal created")
        success_count += 1
    else:
        logger.error("❌ Failed to create dashboard refresh signal")
    
    # Phase 3 Summary
    logger.info(f"\nPHASE 3 SUMMARY: {success_count}/{total_tasks} tasks successful")
    return success_count >= 3  # Allow one failure

# PHASE 4: System Validation & Cleanup
def phase4_system_cleanup(logger):
    """
    Phase 4: System Validation & Cleanup (8:30 PM)
    - Validate all updates completed
    - Archive old files (data retention)
    - Generate summary report
    - Cleanup logs
    """
    logger.info("=" * 60)
    logger.info("PHASE 4: SYSTEM VALIDATION & CLEANUP")
    logger.info("=" * 60)
    
    success_count = 0
    total_tasks = 4
    
    # Task 1: Validate system state
    logger.info("Task 1/4: Validating system state...")
    
    def validate_system_state():
        current_week = get_current_week()
        
        # Check that key files exist and have recent timestamps
        key_files = [
            DATA_DIR / f"cfbd_team_stats_2025_week{current_week}.csv",
            DATA_DIR / "cfbd_team_stats_2025_week1.csv"
        ]
        
        recent_threshold = datetime.now() - timedelta(hours=2)
        
        for file_path in key_files:
            if not file_path.exists():
                raise Exception(f"Key file missing: {file_path}")
            
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_mtime < recent_threshold:
                logger.warning(f"File {file_path} not recently updated")
        
        return True
    
    result, success = retry_with_backoff(validate_system_state, max_attempts=2)
    if success:
        logger.info("✅ System state validation passed")
        success_count += 1
    else:
        logger.error("❌ System state validation failed")
    
    # Task 2: Archive old data files (data retention)
    logger.info(f"Task 2/4: Archiving data older than {WEEKS_TO_KEEP} weeks...")
    
    def archive_old_data():
        current_week = get_current_week()
        cutoff_week = max(0, current_week - WEEKS_TO_KEEP)
        
        archived_count = 0
        
        # Archive old weekly stats files
        pattern = str(DATA_DIR / "cfbd_team_stats_2025_week*.csv")
        for file_path in glob.glob(pattern):
            file_name = Path(file_path).name
            try:
                # Extract week number from filename
                week_str = file_name.replace("cfbd_team_stats_2025_week", "").replace(".csv", "")
                if week_str.isdigit():
                    week_num = int(week_str)
                    if week_num < cutoff_week and week_num > 0:  # Don't archive week0 or week1
                        archive_path = ARCHIVE_DIR / f"{datetime.now().strftime('%Y%m%d')}_{file_name}"
                        shutil.move(file_path, archive_path)
                        archived_count += 1
            except (ValueError, Exception) as e:
                logger.warning(f"Could not process file {file_name}: {e}")
        
        # Archive old results files
        results_pattern = str(DATA_DIR / "results_tracking_*.csv")
        for file_path in glob.glob(results_pattern):
            file_stat = Path(file_path).stat()
            file_age = datetime.now() - datetime.fromtimestamp(file_stat.st_mtime)
            
            if file_age > timedelta(weeks=WEEKS_TO_KEEP):
                archive_path = ARCHIVE_DIR / f"{datetime.now().strftime('%Y%m%d')}_{Path(file_path).name}"
                shutil.move(file_path, archive_path)
                archived_count += 1
        
        return archived_count
    
    result, success = retry_with_backoff(archive_old_data, max_attempts=2)
    if success:
        logger.info(f"✅ Data archival completed: {result} files archived")
        success_count += 1
    else:
        logger.error("❌ Data archival failed")
    
    # Task 3: Cleanup old log files
    logger.info(f"Task 3/4: Cleaning up old log files (keep last {MAX_LOG_FILES})...")
    
    def cleanup_logs():
        log_files = list(LOGS_DIR.glob("*.log"))
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)  # Newest first
        
        deleted_count = 0
        for old_log in log_files[MAX_LOG_FILES:]:  # Keep only the newest MAX_LOG_FILES
            try:
                old_log.unlink()
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Could not delete {old_log}: {e}")
        
        return deleted_count
    
    result, success = retry_with_backoff(cleanup_logs, max_attempts=2)
    if success:
        logger.info(f"✅ Log cleanup completed: {result} old logs removed")
        success_count += 1
    else:
        logger.error("❌ Log cleanup failed")
    
    # Task 4: Generate summary report
    logger.info("Task 4/4: Generating summary report...")
    
    def generate_summary():
        current_week = get_current_week()
        summary = {
            "workflow_time": datetime.now().isoformat(),
            "current_week": current_week,
            "next_week": current_week + 1,
            "phases_completed": 4,
            "data_files_current": len(list(DATA_DIR.glob("*.csv"))),
            "archived_files": len(list(ARCHIVE_DIR.glob("*.csv"))),
            "log_files": len(list(LOGS_DIR.glob("*.log")))
        }
        
        # Save summary report
        summary_file = LOGS_DIR / f"sunday_workflow_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        import json
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary
    
    result, success = retry_with_backoff(generate_summary, max_attempts=2)
    if success:
        logger.info(f"✅ Summary report generated: {result}")
        success_count += 1
    else:
        logger.error("❌ Summary report generation failed")
    
    # Phase 4 Summary
    logger.info(f"\nPHASE 4 SUMMARY: {success_count}/{total_tasks} tasks successful")
    return success_count >= 3  # Allow one failure

def run_enhanced_sunday_workflow(logger, specific_week=None):
    """
    Run the complete enhanced Sunday workflow
    """
    logger.info("🚀 STARTING ENHANCED SUNDAY WORKFLOW")
    logger.info(f"Time: {datetime.now().strftime('%A, %B %d, %Y at %H:%M:%S')}")
    logger.info("=" * 80)
    
    workflow_start_time = datetime.now()
    phases_completed = 0
    total_phases = 4
    
    try:
        # PHASE 1: Data Collection & Updates
        if phase1_data_collection(logger):
            phases_completed += 1
            logger.info("✅ PHASE 1 COMPLETED SUCCESSFULLY")
        else:
            logger.error("❌ PHASE 1 FAILED - Continuing with remaining phases")
        
        # PHASE 2: Results & Performance Analysis
        if phase2_results_analysis(logger, specific_week):
            phases_completed += 1
            logger.info("✅ PHASE 2 COMPLETED SUCCESSFULLY")
        else:
            logger.error("❌ PHASE 2 FAILED - Continuing with remaining phases")
        
        # PHASE 3: Next Week Preparation
        if phase3_next_week_preparation(logger):
            phases_completed += 1
            logger.info("✅ PHASE 3 COMPLETED SUCCESSFULLY")
        else:
            logger.error("❌ PHASE 3 FAILED - Continuing with remaining phases")
        
        # PHASE 4: System Validation & Cleanup
        if phase4_system_cleanup(logger):
            phases_completed += 1
            logger.info("✅ PHASE 4 COMPLETED SUCCESSFULLY")
        else:
            logger.error("❌ PHASE 4 FAILED")
        
    except Exception as e:
        logger.error(f"💥 Unexpected error in workflow: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Final Summary
    workflow_duration = datetime.now() - workflow_start_time
    
    logger.info("=" * 80)
    logger.info("🏁 ENHANCED SUNDAY WORKFLOW SUMMARY")
    logger.info(f"⏱️ Total Duration: {workflow_duration}")
    logger.info(f"✅ Phases Completed: {phases_completed}/{total_phases}")
    logger.info(f"📅 Completed: {datetime.now().strftime('%A, %B %d, %Y at %H:%M:%S')}")
    
    if phases_completed == total_phases:
        logger.info("🎉 ENHANCED SUNDAY WORKFLOW COMPLETED SUCCESSFULLY!")
        return True
    elif phases_completed >= 2:
        logger.warning(f"⚠️ Workflow completed with {total_phases - phases_completed} phase(s) failed - PARTIAL SUCCESS")
        return True  # Partial success is still acceptable
    else:
        logger.error(f"💥 WORKFLOW FAILED - Only {phases_completed} phases completed")
        return False

def main():
    """Main entry point for enhanced Sunday workflow"""
    parser = argparse.ArgumentParser(description="Enhanced NCAA Football Sunday Automation Workflow")
    parser.add_argument(
        "--mode", 
        choices=["full", "phase1", "phase2", "phase3", "phase4"],
        default="full",
        help="Workflow mode: 'full' (all phases) or specific phase"
    )
    parser.add_argument(
        "--week", 
        type=int, 
        help="Specific week number for results tracking"
    )
    parser.add_argument(
        "--quiet", 
        action="store_true",
        help="Reduce console output"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging()
    
    if not args.quiet:
        print("\nENHANCED NCAA FOOTBALL SUNDAY WORKFLOW")
        print(f"Mode: {args.mode.title()}")
        print(f"Time: {datetime.now().strftime('%A, %B %d, %Y at %H:%M:%S')}")
        print("=" * 60)
    
    success = False
    
    try:
        if args.mode == "full":
            success = run_enhanced_sunday_workflow(logger, args.week)
        elif args.mode == "phase1":
            success = phase1_data_collection(logger)
        elif args.mode == "phase2":
            success = phase2_results_analysis(logger, args.week)
        elif args.mode == "phase3":
            success = phase3_next_week_preparation(logger)
        elif args.mode == "phase4":
            success = phase4_system_cleanup(logger)
        
        if success:
            if not args.quiet:
                print(f"\n✅ [SUCCESS] {args.mode.title()} workflow completed!")
            sys.exit(0)
        else:
            if not args.quiet:
                print(f"\n❌ [FAILED] {args.mode.title()} workflow encountered errors!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Workflow interrupted by user")
        print("\n🛑 Workflow interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Unexpected error in enhanced Sunday workflow: {str(e)}")
        if not args.quiet:
            print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()