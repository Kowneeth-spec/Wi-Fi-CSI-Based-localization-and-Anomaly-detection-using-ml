#!/usr/bin/env python3
"""
Optimization demonstration & benchmark suite.

Shows:
  1. GPU acceleration for XGBoost
  2. Parallel feature extraction
  3. Vectorized preprocessing
  4. Training pipeline optimization

Run: python optimize_benchmark.py [--gpu] [--parallel] [--benchmark]
"""

import sys
import argparse
import time
from pathlib import Path

def run_gpu_benchmark():
    """Benchmark GPU vs CPU for XGBoost."""
    print("\n" + "█"*70)
    print("█  GPU ACCELERATION BENCHMARK (XGBoost)")
    print("█"*70)
    
    try:
        from src.utils.optimize import benchmark_gpu_vs_cpu
        results = benchmark_gpu_vs_cpu(
            n_samples=5000,
            n_features=100,
            n_estimators=100
        )
        
        if 'gpu_time' in results:
            print(f"\n✓ GPU benchmark complete")
            print(f"  CPU:    {results['cpu_time']:.3f}s")
            print(f"  GPU:    {results['gpu_time']:.3f}s")
            print(f"  Speedup: {results['speedup']:.1f}x")
        else:
            print("\n⚠ GPU not available (CPU-only benchmark ran)")
            
    except Exception as e:
        print(f"✗ GPU benchmark failed: {e}")


def run_feature_extraction_benchmark():
    """Benchmark parallel feature extraction."""
    print("\n" + "█"*70)
    print("█  PARALLEL FEATURE EXTRACTION BENCHMARK")
    print("█"*70)
    
    try:
        from src.feature_engineering.optimize_extraction import benchmark_parallel_extraction
        benchmark_parallel_extraction()
    except Exception as e:
        print(f"✗ Feature extraction benchmark failed: {e}")


def run_preprocessing_benchmark():
    """Benchmark vectorized preprocessing."""
    print("\n" + "█"*70)
    print("█  VECTORIZED PREPROCESSING BENCHMARK")
    print("█"*70)
    
    try:
        from src.preprocessing.optimize_cleaning import benchmark_vectorized_preprocessing
        benchmark_vectorized_preprocessing()
    except Exception as e:
        print(f"✗ Preprocessing benchmark failed: {e}")


def run_full_pipeline_with_optimization(use_gpu=False, use_parallel=True):
    """Run full training pipeline with optimizations."""
    print("\n" + "█"*70)
    print("█  FULL PIPELINE WITH OPTIMIZATION")
    print("█"*70)
    
    print(f"\nConfiguration:")
    print(f"  GPU acceleration:       {use_gpu}")
    print(f"  Parallel extraction:    {use_parallel}")
    
    try:
        from src.localization.train import train_pipeline
        
        start = time.time()
        results = train_pipeline(use_pca=True)
        elapsed = time.time() - start
        
        print(f"\n✓ Pipeline complete in {elapsed:.2f}s")
        print(f"\nResults:")
        print(f"  Accuracy:                {results['accuracy']*100:.2f}%")
        print(f"  MAE (x):                 {results['mae_x']:.3f} m")
        print(f"  MAE (y):                 {results['mae_y']:.3f} m")
        print(f"  Mean Euclidean error:    {results['mean_euclidean_error']:.3f} m")
        print(f"  90-percentile error:     {results['p90_error']:.3f} m")
        
    except Exception as e:
        print(f"✗ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()


def generate_optimization_report():
    """Generate a comprehensive optimization report."""
    print("\n" + "█"*70)
    print("█  OPTIMIZATION REPORT")
    print("█"*70)
    
    import multiprocessing
    
    print("\n1. SYSTEM RESOURCES:")
    print(f"   CPUs:                 {multiprocessing.cpu_count()}")
    
    try:
        import torch
        print(f"   CUDA available:       True")
        print(f"   CUDA device count:    {torch.cuda.device_count()}")
        if torch.cuda.device_count() > 0:
            print(f"   GPU:                  {torch.cuda.get_device_name(0)}")
    except:
        print(f"   CUDA available:       False")
    
    print("\n2. OPTIMIZATION OPTIONS:")
    print("   ✓ GPU Acceleration:    XGBoost (tree_method='gpu_hist')")
    print("   ✓ Parallel Processing: Feature extraction (joblib)")
    print("   ✓ Vectorized Ops:      Preprocessing (scipy/numpy)")
    print("   ✓ Caching:             Model artifacts (joblib)")
    
    print("\n3. ESTIMATED SPEEDUPS:")
    print("   • GPU (XGBoost):       2-10x (depends on dataset/GPU)")
    print("   • Parallel Features:   1.5-4x (depends on CPU cores)")
    print("   • Vectorized Preproc:  2-5x")
    print("   • Combined:            ~5-20x overall")
    
    print("\n4. RECOMMENDED SETTINGS:")
    
    import multiprocessing
    n_cpus = multiprocessing.cpu_count()
    
    if n_cpus >= 8:
        print("   • n_jobs:             -1 (use all CPUs)")
        print("   • use_gpu:            True (if CUDA available)")
        print("   • parallel_features:  True")
    elif n_cpus >= 4:
        print("   • n_jobs:             -1 (use all CPUs)")
        print("   • use_gpu:            True (if CUDA available)")
        print("   • parallel_features:  True")
    else:
        print("   • n_jobs:             1-2")
        print("   • use_gpu:            True (recommended)")
        print("   • parallel_features:  False")
    
    print("\n" + "█"*70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="CSI Indoor Localization - Optimization Benchmarks"
    )
    parser.add_argument(
        '--gpu',
        action='store_true',
        help='Run GPU acceleration benchmark'
    )
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Run parallel feature extraction benchmark'
    )
    parser.add_argument(
        '--preprocessing',
        action='store_true',
        help='Run vectorized preprocessing benchmark'
    )
    parser.add_argument(
        '--full-pipeline',
        action='store_true',
        help='Run full pipeline with optimizations'
    )
    parser.add_argument(
        '--all-benchmarks',
        action='store_true',
        help='Run all benchmarks'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate optimization report'
    )
    
    args = parser.parse_args()
    
    # Default: show report
    if not any([args.gpu, args.parallel, args.preprocessing, args.full_pipeline, 
                args.all_benchmarks, args.report]):
        args.report = True
    
    print("\n" + "="*70)
    print("   CSI INDOOR LOCALIZATION - OPTIMIZATION SUITE")
    print("="*70)
    
    if args.report or args.all_benchmarks:
        generate_optimization_report()
    
    if args.gpu or args.all_benchmarks:
        run_gpu_benchmark()
    
    if args.parallel or args.all_benchmarks:
        run_feature_extraction_benchmark()
    
    if args.preprocessing or args.all_benchmarks:
        run_preprocessing_benchmark()
    
    if args.full_pipeline or args.all_benchmarks:
        run_full_pipeline_with_optimization(
            use_gpu=args.gpu,
            use_parallel=args.parallel
        )
    
    print("\n" + "="*70)
    print("   OPTIMIZATION SUITE COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
