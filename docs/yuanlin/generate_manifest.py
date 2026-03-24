#!/usr/bin/env python3
"""
Phase 0: Generate file manifest for Skia source-level documentation.
Scans the codebase, identifies .h/.cpp pairs, and creates a JSON manifest.
"""

import os
import json
from pathlib import Path
from collections import defaultdict

SKIA_ROOT = Path("/Users/yuanlin/workspace/skia")
DOCS_ROOT = SKIA_ROOT / "docs" / "yuanlin"

# File extensions to include
EXTENSIONS = {'.h', '.cpp', '.cc', '.mm', '.m', '.rs', '.py', '.go', '.js', '.ts'}

# Directories to exclude
EXCLUDE_DIRS = {
    'tests', 'gm', 'bench', '.git', 'third_party', 'node_modules', 'resources',
    'docs',  # don't recurse into docs/
}

# Specific paths to exclude
EXCLUDE_PATHS = {
    'docs/examples',
    'tests/sksl',
}

def should_exclude(rel_path: str) -> bool:
    """Check if a path should be excluded."""
    parts = rel_path.split(os.sep)
    # Check top-level directory exclusions
    if parts[0] in EXCLUDE_DIRS:
        return True
    # Check specific path exclusions
    for exc in EXCLUDE_PATHS:
        if rel_path.startswith(exc):
            return True
    return False

def scan_source_files():
    """Scan the codebase for all source files."""
    files = []
    for root, dirs, filenames in os.walk(SKIA_ROOT):
        # Skip hidden directories and excluded directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in EXCLUDE_DIRS]

        for fname in filenames:
            fpath = Path(root) / fname
            ext = fpath.suffix.lower()
            if ext not in EXTENSIONS:
                continue

            rel_path = str(fpath.relative_to(SKIA_ROOT))
            if should_exclude(rel_path):
                continue

            line_count = 0
            try:
                with open(fpath, 'r', errors='replace') as f:
                    line_count = sum(1 for _ in f)
            except:
                pass

            files.append({
                'path': rel_path,
                'ext': ext,
                'lines': line_count,
                'stem': fpath.stem,
                'dir': str(fpath.parent.relative_to(SKIA_ROOT)),
            })

    return files

def build_pairs(files):
    """Build .h/.cpp pairs and create document entries."""
    # Index files by directory and stem
    by_dir_stem = defaultdict(list)
    for f in files:
        key = (f['dir'], f['stem'])
        by_dir_stem[key].append(f)

    # Index include/ headers for cross-directory pairing
    # include/X/Y.h -> src/X/Y.cpp
    include_headers = {}
    for f in files:
        if f['path'].startswith('include/') and f['ext'] == '.h':
            # Map include/core/SkFoo.h -> core/SkFoo
            parts = f['dir'].split(os.sep)
            if len(parts) >= 2:
                sub_path = os.sep.join(parts[1:])  # remove 'include'
                include_headers[(sub_path, f['stem'])] = f

    # Track which files have been paired
    paired_files = set()
    documents = []
    doc_id = 0

    # Step 1: Same-directory pairs (.h + .cpp/.cc/.mm)
    cpp_exts = {'.cpp', '.cc', '.mm', '.m'}
    for (dir_path, stem), group in by_dir_stem.items():
        headers = [f for f in group if f['ext'] == '.h']
        impls = [f for f in group if f['ext'] in cpp_exts]

        if headers and impls:
            # Pair them
            all_paths = [f['path'] for f in headers + impls]
            total_lines = sum(f['lines'] for f in headers + impls)

            # Determine output path (implementation directory)
            out_dir = dir_path
            out_name = stem + '.md'
            out_path = str(DOCS_ROOT / out_dir / out_name)

            doc_id += 1
            documents.append({
                'id': doc_id,
                'sources': all_paths,
                'output': str(Path(out_dir) / out_name),
                'total_lines': total_lines,
                'type': 'pair_same_dir',
            })
            for f in headers + impls:
                paired_files.add(f['path'])

    # Step 2: Cross-directory pairs (include/X/Y.h + src/X/Y.cpp)
    for f in files:
        if f['path'].startswith('src/') and f['ext'] in cpp_exts and f['path'] not in paired_files:
            parts = f['dir'].split(os.sep)
            if len(parts) >= 2:
                sub_path = os.sep.join(parts[1:])  # remove 'src'
                key = (sub_path, f['stem'])
                if key in include_headers:
                    header = include_headers[key]
                    if header['path'] not in paired_files:
                        total_lines = f['lines'] + header['lines']
                        out_dir = f['dir']  # src/ directory
                        out_name = f['stem'] + '.md'

                        doc_id += 1
                        documents.append({
                            'id': doc_id,
                            'sources': [header['path'], f['path']],
                            'output': str(Path(out_dir) / out_name),
                            'total_lines': total_lines,
                            'type': 'pair_cross_dir',
                        })
                        paired_files.add(f['path'])
                        paired_files.add(header['path'])

    # Step 3: Unpaired files - each gets its own document
    for f in files:
        if f['path'] not in paired_files:
            out_dir = f['dir']
            out_name = f['stem'] + '.md'
            out_path = str(Path(out_dir) / out_name)

            doc_id += 1
            documents.append({
                'id': doc_id,
                'sources': [f['path']],
                'output': out_path,
                'total_lines': f['lines'],
                'type': 'single',
            })
            paired_files.add(f['path'])

    return documents

def assign_phases(documents):
    """Assign each document to a phase based on its directory."""
    for doc in documents:
        first_source = doc['sources'][0]
        if first_source.startswith('include/'):
            # Check if it was cross-dir paired (output in src/)
            if doc['type'] == 'pair_cross_dir':
                doc['phase'] = 2  # Goes with src/
            else:
                doc['phase'] = 1
        elif first_source.startswith('src/core/') or first_source.startswith('src/base/') or first_source.startswith('src/opts/') or first_source.startswith('src/lazy/'):
            doc['phase'] = 2
        elif first_source.startswith('src/gpu/'):
            doc['phase'] = 3
        elif first_source.startswith('src/'):
            doc['phase'] = 4
        elif first_source.startswith('modules/'):
            doc['phase'] = 5
        else:
            doc['phase'] = 6

    return documents

def assign_batches(documents):
    """Assign batch numbers within each phase."""
    # Group by phase
    by_phase = defaultdict(list)
    for doc in documents:
        by_phase[doc['phase']].append(doc)

    for phase, docs in by_phase.items():
        # Sort by directory then by name for locality
        docs.sort(key=lambda d: d['output'])

        # Determine batch sizes based on file sizes
        batch_num = 1
        current_batch = []
        current_lines = 0

        for doc in docs:
            # Super large files get their own batch
            if doc['total_lines'] > 3000:
                if current_batch:
                    for d in current_batch:
                        d['batch'] = f"{phase}.{batch_num:02d}"
                    batch_num += 1
                    current_batch = []
                    current_lines = 0

                doc['batch'] = f"{phase}.{batch_num:02d}"
                batch_num += 1
                continue

            current_batch.append(doc)
            current_lines += doc['total_lines']

            # Determine max docs per batch based on size category
            max_docs = 12
            if doc['total_lines'] > 1500:
                max_docs = 3
            elif doc['total_lines'] > 500:
                max_docs = 6
            elif doc['total_lines'] > 100:
                max_docs = 10
            else:
                max_docs = 15

            if len(current_batch) >= max_docs or current_lines > 8000:
                for d in current_batch:
                    d['batch'] = f"{phase}.{batch_num:02d}"
                batch_num += 1
                current_batch = []
                current_lines = 0

        # Remaining
        if current_batch:
            for d in current_batch:
                d['batch'] = f"{phase}.{batch_num:02d}"

    return documents

def create_directories(documents):
    """Create all output directories."""
    dirs_created = set()
    for doc in documents:
        out_dir = DOCS_ROOT / Path(doc['output']).parent
        if str(out_dir) not in dirs_created:
            out_dir.mkdir(parents=True, exist_ok=True)
            dirs_created.add(str(out_dir))
    return len(dirs_created)

def main():
    print("Scanning source files...")
    files = scan_source_files()
    print(f"Found {len(files)} source files")

    # Stats by extension
    by_ext = defaultdict(int)
    for f in files:
        by_ext[f['ext']] += 1
    for ext, count in sorted(by_ext.items()):
        print(f"  {ext}: {count}")

    print("\nBuilding document pairs...")
    documents = build_pairs(files)
    print(f"Total documents to generate: {len(documents)}")

    # Stats by type
    by_type = defaultdict(int)
    for d in documents:
        by_type[d['type']] += 1
    for t, count in sorted(by_type.items()):
        print(f"  {t}: {count}")

    print("\nAssigning phases...")
    documents = assign_phases(documents)

    # Stats by phase
    by_phase = defaultdict(int)
    for d in documents:
        by_phase[d['phase']] += 1
    for p, count in sorted(by_phase.items()):
        print(f"  Phase {p}: {count} documents")

    print("\nAssigning batches...")
    documents = assign_batches(documents)

    # Stats by batch
    batches = defaultdict(list)
    for d in documents:
        batches[d['batch']].append(d)
    print(f"Total batches: {len(batches)}")

    print("\nCreating output directories...")
    dirs_count = create_directories(documents)
    print(f"Created/verified {dirs_count} directories")

    # Save manifest
    manifest_path = DOCS_ROOT / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump({
            'total_files': len(files),
            'total_documents': len(documents),
            'total_batches': len(batches),
            'documents': documents,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nManifest saved to {manifest_path}")

    # Save batch summary
    summary_path = DOCS_ROOT / "batch_summary.json"
    batch_summary = {}
    for batch_id, docs in sorted(batches.items()):
        batch_summary[batch_id] = {
            'count': len(docs),
            'total_lines': sum(d['total_lines'] for d in docs),
            'documents': [d['output'] for d in docs],
        }
    with open(summary_path, 'w') as f:
        json.dump(batch_summary, f, indent=2, ensure_ascii=False)
    print(f"Batch summary saved to {summary_path}")

if __name__ == '__main__':
    main()
