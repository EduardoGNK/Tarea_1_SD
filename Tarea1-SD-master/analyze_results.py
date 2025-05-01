#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import glob
import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Visualization settings
FIGURE_DIMENSIONS = (14, 8)
VISUALIZATION_DIR = "visualization_output"
IMAGE_QUALITY = 300
USE_DARK_MODE = False  # Set to True for dark theme

# Ensure output directory exists
os.makedirs(VISUALIZATION_DIR, exist_ok=True)
print(f"📁 Output directory ready: {VISUALIZATION_DIR}")

# Set visualization theme
if USE_DARK_MODE:
    plt.style.use('dark_background')
else:
    plt.style.use('seaborn-v0_8-whitegrid')

def find_result_files():
    """Locate all JSON result files in the current directory"""
    json_files = glob.glob("*.json")
    print(f"🔍 Located {len(json_files)} JSON files: {', '.join(json_files)}")
    return json_files

def import_benchmark_data(file_list):
    """Import benchmark data from JSON files"""
    benchmark_data = []
    
    # Try consolidated file first
    main_results_file = "all_simulation_results.json"
    if main_results_file in file_list:
        try:
            with open(main_results_file, "r") as f:
                data = json.load(f)
                print(f"📊 Imported {len(data)} benchmark results from main file")
                return data
        except Exception as e: 
            print(f"⚠️ Error importing main file: {e}")
    
    # Fall back to individual files
    print("📑 Importing individual result files...")
    for filename in file_list:
        if filename.startswith("results_") and not filename.endswith(".csv"):
            try:
                with open(filename, "r") as f:
                    content = json.load(f)
                    if isinstance(content, dict):
                        benchmark_data.append(content)
                        print(f"  ✓ Imported single result from {filename}")
                    elif isinstance(content, list):
                        benchmark_data.extend(content)
                        print(f"  ✓ Imported {len(content)} results from {filename}")
            except Exception as e:
                print(f"  ✗ Error importing {filename}: {e}")
    
    print(f"📈 Total benchmark results imported: {len(benchmark_data)}")
    return benchmark_data

def generate_performance_charts(dataset):
    """Create visual performance charts for cache metrics"""
    metrics_to_visualize = {
        "hit_rate": {
            "title": "Cache Hit Rate Comparison by Strategy and Distribution",
            "ylabel": "Hit Rate (%)",
            "format": lambda x: f"{x:.1%}"
        },
        "avg_latency": {
            "title": "Response Latency Comparison by Strategy and Distribution",
            "ylabel": "Latency (ms)",
            "format": lambda x: f"{x*1000:.2f} ms"
        }
    }
    
    for metric, config in metrics_to_visualize.items():
        if metric not in dataset.columns:
            print(f"⚠️ Metric '{metric}' not found in dataset")
            continue
            
        plt.figure(figsize=FIGURE_DIMENSIONS)
        plot = sns.barplot(
            x="cache_policy", 
            y=metric, 
            hue="distribution", 
            data=dataset,
            palette="viridis"
        )
        
        # Add value labels
        for idx, bar in enumerate(plot.patches):
            height = bar.get_height()
            if not pd.isna(height):
                plot.text(
                    bar.get_x() + bar.get_width()/2.,
                    height + 0.02 * max(dataset[metric]),
                    config["format"](height),
                    ha='center', 
                    fontsize=9
                )
        
        plt.title(config["title"], fontsize=14)
        plt.xlabel("Cache Strategy", fontsize=12)
        plt.ylabel(config["ylabel"], fontsize=12)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        # Save chart
        output_file = f"{metric}_analysis.png"
        plt.savefig(os.path.join(VISUALIZATION_DIR, output_file), dpi=IMAGE_QUALITY)
        print(f"📊 Generated {output_file}")

def visualize_cache_performance(dataset):
    """Create visualization of cache hits vs misses"""
    if "hits" not in dataset.columns or "misses" not in dataset.columns:
        print("⚠️ Hit/miss metrics not available in dataset")
        return
        
    plt.figure(figsize=FIGURE_DIMENSIONS)
    
    # Transform data for visualization
    reshaped_data = pd.melt(
        dataset, 
        id_vars=["distribution", "cache_policy"], 
        value_vars=["hits", "misses"],
        var_name="result_type", 
        value_name="count"
    )
    
    # Create chart
    plot = sns.barplot(
        x="cache_policy", 
        y="count", 
        hue="result_type", 
        data=reshaped_data,
        palette=["#2ecc71", "#e74c3c"]
    )
    
    # Add value labels with percentages
    for idx, bar in enumerate(plot.patches):
        height = bar.get_height()
        
        # Calculate percentage based on total queries
        if idx % 2 == 0:  # Hit bar
            policy = reshaped_data.iloc[idx]["cache_policy"]
            dist = reshaped_data.iloc[idx]["distribution"]
            total = dataset[(dataset["cache_policy"] == policy) & 
                           (dataset["distribution"] == dist)]["total_queries"].values[0]
            percentage = height / total * 100
            label = f"{int(height)}\n({percentage:.1f}%)"
        else:  # Miss bar
            policy = reshaped_data.iloc[idx-1]["cache_policy"]
            dist = reshaped_data.iloc[idx-1]["distribution"]
            total = dataset[(dataset["cache_policy"] == policy) & 
                           (dataset["distribution"] == dist)]["total_queries"].values[0]
            percentage = height / total * 100
            label = f"{int(height)}\n({percentage:.1f}%)"
        
        plot.text(
            bar.get_x() + bar.get_width()/2.,
            height/2,
            label,
            ha='center',
            va='center',
            fontsize=9,
            color='white',
            fontweight='bold'
        )
    
    plt.title("Cache Hit vs Miss Analysis by Strategy and Distribution", fontsize=14)
    plt.xlabel("Cache Strategy", fontsize=12)
    plt.ylabel("Count", fontsize=12)
    plt.legend(title="Result Type")
    plt.grid(axis='y', linestyle='--', alpha=0.4)
    plt.tight_layout()
    
    # Save chart
    output_file = "hits_misses_analysis.png"
    plt.savefig(os.path.join(VISUALIZATION_DIR, output_file), dpi=IMAGE_QUALITY)
    print(f"📊 Generated {output_file}")

def generate_summary_table(dataset):
    """Generate summary comparison table"""
    if dataset.empty:
        print("⚠️ No data available for summary table")
        return
        
    # Select and format relevant columns
    summary = dataset[[
        "distribution", 
        "cache_policy", 
        "hit_rate", 
        "avg_latency", 
        "hits", 
        "misses"
    ]].copy()
    
    # Format for readability
    summary["hit_rate"] = summary["hit_rate"].apply(lambda x: f"{x:.2%}")
    summary["avg_latency"] = summary["avg_latency"].apply(
        lambda x: f"{x*1000:.2f} ms"
    )
    
    # Sort by strategy and distribution
    summary = summary.sort_values(["distribution", "cache_policy"])
    
    # Display in console
    print("\n📋 Performance Summary Table:")
    print(summary.to_string(index=False))
    
    # Export to CSV
    csv_filename = "cache_performance_comparison.csv"
    summary.to_csv(csv_filename, index=False)
    print(f"📄 Exported summary table to {csv_filename}")
    
    return summary

def main():
    """Main analysis function"""
    print("🚀 Starting cache performance analysis")
    print(f"📅 Analysis timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Find and import result files
    json_files = find_result_files()
    benchmark_results = import_benchmark_data(json_files)
    
    if not benchmark_results:
        print("❌ No benchmark results found to analyze")
        return
    
    # Convert to DataFrame for analysis
    results_df = pd.DataFrame(benchmark_results)
    
    # Show available metrics
    print("\n📊 Available metrics for analysis:")
    print(", ".join(results_df.columns.tolist()))
    
    # Generate visualizations
    generate_performance_charts(results_df)
    visualize_cache_performance(results_df)
    generate_summary_table(results_df)
    
    print("\n✅ Analysis complete! Results available in the visualization_output directory.")

if __name__ == "__main__":
    main()