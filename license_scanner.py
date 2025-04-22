import os
import re
import json
import hashlib
from typing import Dict, List, Set, Tuple, Optional
import logging

logger = logging.getLogger("vibe_scanner")

# Common open source licenses and their identifiers
KNOWN_LICENSES = {
    'MIT': [
        r'MIT License',
        r'Permission is hereby granted, free of charge',
        r'MIT',
    ],
    'Apache-2.0': [
        r'Apache License',
        r'Licensed under the Apache License',
        r'Apache 2.0',
    ],
    'GPL-3.0': [
        r'GNU GENERAL PUBLIC LICENSE',
        r'GPL-3',
        r'GPLv3',
    ],
    'GPL-2.0': [
        r'GNU GENERAL PUBLIC LICENSE Version 2',
        r'GPL-2',
        r'GPLv2',
    ],
    'BSD-3-Clause': [
        r'BSD 3-Clause',
        r'Redistribution and use in source and binary forms',
    ],
    'LGPL-3.0': [
        r'GNU LESSER GENERAL PUBLIC LICENSE',
        r'LGPL-3',
        r'LGPLv3',
    ]
}

class LicenseScanner:
    def __init__(self):
        self.file_hashes: Dict[str, str] = {}
        self.similar_code_blocks: List[Tuple[str, str, float]] = []
        
    def scan_directory(self, directory: str) -> Dict:
        """Scan a directory for license issues and code similarities."""
        results = {
            'license_findings': [],
            'similar_code_blocks': [],
            'license_conflicts': [],
            'missing_licenses': []
        }
        
        # Find all code files
        code_files = self._find_code_files(directory)
        
        # Check for project-level license
        project_license = self._detect_project_license(directory)
        if not project_license:
            results['missing_licenses'].append({
                'type': 'project',
                'path': directory,
                'message': 'No project-level LICENSE file found'
            })
        
        # Scan each file
        for file_path in code_files:
            file_results = self._scan_file(file_path, project_license)
            results['license_findings'].extend(file_results.get('license_findings', []))
            results['similar_code_blocks'].extend(file_results.get('similar_code_blocks', []))
            
            # Check for license conflicts
            if file_results.get('license') and project_license:
                if not self._are_licenses_compatible(project_license, file_results['license']):
                    results['license_conflicts'].append({
                        'file': file_path,
                        'project_license': project_license,
                        'file_license': file_results['license'],
                        'message': f'File license {file_results["license"]} may be incompatible with project license {project_license}'
                    })
        
        return results
    
    def _find_code_files(self, directory: str) -> List[str]:
        """Find all code files in the directory."""
        code_extensions = {'.py', '.js', '.ts', '.go', '.rb', '.java', '.cpp', '.c', '.h', '.hpp'}
        code_files = []
        
        for root, _, files in os.walk(directory):
            for file in files:
                if os.path.splitext(file)[1] in code_extensions:
                    code_files.append(os.path.join(root, file))
        
        return code_files
    
    def _detect_project_license(self, directory: str) -> Optional[str]:
        """Detect the project's main license."""
        license_files = ['LICENSE', 'LICENSE.txt', 'LICENSE.md', 'COPYING']
        
        for license_file in license_files:
            license_path = os.path.join(directory, license_file)
            if os.path.exists(license_path):
                with open(license_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    return self._identify_license(content)
        
        return None
    
    def _scan_file(self, file_path: str, project_license: Optional[str]) -> Dict:
        """Scan an individual file for license issues and code similarities."""
        results = {
            'license_findings': [],
            'similar_code_blocks': [],
            'license': None
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for file-level license
            file_license = self._extract_file_license(content)
            if file_license:
                results['license'] = file_license
            
            # Generate file hash for similarity detection
            file_hash = self._hash_content(content)
            self.file_hashes[file_path] = file_hash
            
            # Check for code similarities
            similar_files = self._find_similar_code(file_path, content)
            results['similar_code_blocks'].extend(similar_files)
            
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {str(e)}")
        
        return results
    
    def _identify_license(self, content: str) -> Optional[str]:
        """Identify the license type from content."""
        content = content.lower()
        
        for license_type, patterns in KNOWN_LICENSES.items():
            for pattern in patterns:
                if re.search(pattern.lower(), content):
                    return license_type
        
        return None
    
    def _extract_file_license(self, content: str) -> Optional[str]:
        """Extract license information from file comments."""
        # Common comment patterns
        comment_patterns = [
            r'/\*.*?\*/',  # C-style block comments
            r'#.*$',       # Python/Ruby style comments
            r'//.*$'       # C++/JavaScript style comments
        ]
        
        header = content[:1000]  # Check first 1000 characters for license
        
        for pattern in comment_patterns:
            comments = re.findall(pattern, header, re.MULTILINE | re.DOTALL)
            for comment in comments:
                license_type = self._identify_license(comment)
                if license_type:
                    return license_type
        
        return None
    
    def _hash_content(self, content: str) -> str:
        """Generate a hash of the content for similarity checking."""
        # Normalize content by removing comments and whitespace
        normalized = re.sub(r'(/\*.*?\*/|//.*$|#.*$|\s+)', '', content, flags=re.MULTILINE | re.DOTALL)
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def _find_similar_code(self, file_path: str, content: str) -> List[Dict]:
        """Find similar code blocks in other files."""
        similar_blocks = []
        current_hash = self._hash_content(content)
        
        for other_path, other_hash in self.file_hashes.items():
            if other_path != file_path:
                similarity = self._calculate_similarity(current_hash, other_hash)
                if similarity > 0.8:  # 80% similarity threshold
                    similar_blocks.append({
                        'file1': file_path,
                        'file2': other_path,
                        'similarity': similarity,
                        'message': f'High code similarity ({similarity:.2%}) detected'
                    })
        
        return similar_blocks
    
    def _calculate_similarity(self, hash1: str, hash2: str) -> float:
        """Calculate similarity between two hashes."""
        # Simple similarity calculation based on hash comparison
        # In a real implementation, you'd want a more sophisticated algorithm
        same_chars = sum(1 for a, b in zip(hash1, hash2) if a == b)
        return same_chars / len(hash1)
    
    def _are_licenses_compatible(self, license1: str, license2: str) -> bool:
        """Check if two licenses are compatible."""
        # License compatibility matrix
        # This is a simplified version - in reality, you'd want a more comprehensive check
        compatibility_matrix = {
            'MIT': {'MIT', 'Apache-2.0', 'GPL-3.0', 'GPL-2.0', 'BSD-3-Clause', 'LGPL-3.0'},
            'Apache-2.0': {'Apache-2.0', 'MIT', 'BSD-3-Clause'},
            'GPL-3.0': {'GPL-3.0'},
            'GPL-2.0': {'GPL-2.0'},
            'BSD-3-Clause': {'BSD-3-Clause', 'MIT', 'Apache-2.0'},
            'LGPL-3.0': {'LGPL-3.0', 'MIT'}
        }
        
        return (license1 in compatibility_matrix and 
                license2 in compatibility_matrix[license1])
