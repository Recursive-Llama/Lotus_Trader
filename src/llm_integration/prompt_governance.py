"""
Prompt Governance System

Provides enforcement mechanisms to ensure all prompts use the centralized
PromptManager system and prevents hardcoded prompts from being introduced.
"""

import os
import re
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class PromptGovernance:
    """
    Governance system for prompt management and enforcement
    """
    
    def __init__(self, codebase_path: str = None):
        """
        Initialize prompt governance system
        
        Args:
            codebase_path: Path to the codebase root (defaults to current directory)
        """
        if codebase_path is None:
            codebase_path = os.getcwd()
        
        self.codebase_path = Path(codebase_path)
        self.allowed_prompt_locations = [
            "src/llm_integration/prompt_templates/",
            "Module_Design/Specific_Modules/*/pipeline_prompts/"
        ]
        
        # Patterns that indicate hardcoded prompts
        self.forbidden_patterns = [
            r'f""".*You are.*""",  # Hardcoded system messages
            r'prompt\s*=\s*f"""',  # Hardcoded prompt assignments
            r'return\s+f"""',      # Hardcoded return statements
            r'def.*prompt.*f"""',  # Hardcoded prompt methods
            r'"""You are.*"""',    # Alternative hardcoded system messages
        ]
        
        # Compile regex patterns for efficiency
        self.compiled_patterns = [re.compile(pattern, re.MULTILINE | re.DOTALL) 
                                 for pattern in self.forbidden_patterns]
    
    def scan_for_hardcoded_prompts(self, file_path: str = None) -> List[Dict[str, Any]]:
        """
        Scan codebase for hardcoded prompts
        
        Args:
            file_path: Optional specific file to scan (defaults to entire codebase)
            
        Returns:
            List of violations found
        """
        violations = []
        
        if file_path:
            # Scan specific file
            violations.extend(self._scan_file(Path(file_path)))
        else:
            # Scan entire codebase
            for py_file in self.codebase_path.rglob("*.py"):
                # Skip certain directories
                if self._should_skip_file(py_file):
                    continue
                
                violations.extend(self._scan_file(py_file))
        
        return violations
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during scanning"""
        skip_patterns = [
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            ".pytest_cache",
            "test_",
            "_test.py"
        ]
        
        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)
    
    def _scan_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Scan a single file for hardcoded prompts"""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for i, pattern in enumerate(self.compiled_patterns):
                matches = pattern.finditer(content)
                
                for match in matches:
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1
                    
                    violations.append({
                        'file': str(file_path),
                        'line': line_num,
                        'pattern': self.forbidden_patterns[i],
                        'match': match.group()[:100] + "..." if len(match.group()) > 100 else match.group(),
                        'severity': 'high' if 'You are' in match.group() else 'medium'
                    })
        
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}")
        
        return violations
    
    def validate_prompt_usage(self, file_path: str) -> bool:
        """
        Ensure file uses PromptManager, not hardcoded strings
        
        Args:
            file_path: Path to file to validate
            
        Returns:
            True if file uses PromptManager correctly
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if file imports PromptManager
            has_prompt_manager = 'PromptManager' in content or 'prompt_manager' in content
            
            # Check for hardcoded prompts
            has_hardcoded = any(pattern.search(content) for pattern in self.compiled_patterns)
            
            # File is valid if it uses PromptManager and has no hardcoded prompts
            return has_prompt_manager and not has_hardcoded
        
        except Exception as e:
            logger.error(f"Error validating file {file_path}: {e}")
            return False
    
    def enforce_prompt_standards(self) -> Dict[str, Any]:
        """
        Run governance checks and report violations
        
        Returns:
            Summary of governance check results
        """
        logger.info("Running prompt governance checks...")
        
        violations = self.scan_for_hardcoded_prompts()
        
        # Group violations by file
        violations_by_file = {}
        for violation in violations:
            file_path = violation['file']
            if file_path not in violations_by_file:
                violations_by_file[file_path] = []
            violations_by_file[file_path].append(violation)
        
        # Generate summary
        summary = {
            'total_violations': len(violations),
            'files_with_violations': len(violations_by_file),
            'violations_by_file': violations_by_file,
            'high_severity': len([v for v in violations if v['severity'] == 'high']),
            'medium_severity': len([v for v in violations if v['severity'] == 'medium']),
            'compliance_rate': self._calculate_compliance_rate()
        }
        
        logger.info(f"Governance check complete: {summary['total_violations']} violations found")
        return summary
    
    def _calculate_compliance_rate(self) -> float:
        """Calculate compliance rate based on file analysis"""
        total_files = 0
        compliant_files = 0
        
        for py_file in self.codebase_path.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            total_files += 1
            if self.validate_prompt_usage(str(py_file)):
                compliant_files += 1
        
        if total_files == 0:
            return 1.0
        
        return compliant_files / total_files
    
    def suggest_fixes(self, violations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Suggest fixes for prompt violations
        
        Args:
            violations: List of violations to fix
            
        Returns:
            List of suggested fixes
        """
        fixes = []
        
        for violation in violations:
            file_path = violation['file']
            line = violation['line']
            match = violation['match']
            
            # Generate fix suggestion based on violation type
            if 'You are' in match:
                fix = {
                    'file': file_path,
                    'line': line,
                    'type': 'hardcoded_system_message',
                    'suggestion': 'Move system message to YAML template and use PromptManager.get_system_message()',
                    'example': 'system_msg = prompt_manager.get_system_message("template_name")'
                }
            elif 'prompt =' in match:
                fix = {
                    'file': file_path,
                    'line': line,
                    'type': 'hardcoded_prompt_assignment',
                    'suggestion': 'Use PromptManager.format_prompt() instead of hardcoded assignment',
                    'example': 'prompt = prompt_manager.format_prompt("template_name", context)'
                }
            else:
                fix = {
                    'file': file_path,
                    'line': line,
                    'type': 'hardcoded_prompt',
                    'suggestion': 'Extract hardcoded prompt to YAML template',
                    'example': 'Use PromptManager to load prompt from template'
                }
            
            fixes.append(fix)
        
        return fixes
    
    def auto_extract_prompts(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Automatically extract hardcoded prompts to YAML templates
        
        Args:
            file_path: Path to file with hardcoded prompts
            
        Returns:
            List of extracted prompts ready for YAML templates
        """
        extracted_prompts = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find all hardcoded prompts
            for pattern in self.compiled_patterns:
                matches = pattern.finditer(content)
                
                for match in matches:
                    prompt_text = match.group()
                    
                    # Extract prompt content (remove f""" and """)
                    if prompt_text.startswith('f"""') and prompt_text.endswith('"""'):
                        prompt_content = prompt_text[4:-3].strip()
                    elif prompt_text.startswith('"""') and prompt_text.endswith('"""'):
                        prompt_content = prompt_text[3:-3].strip()
                    else:
                        continue
                    
                    # Generate template name based on file and function context
                    template_name = self._generate_template_name(file_path, match.start(), content)
                    
                    extracted_prompts.append({
                        'template_name': template_name,
                        'prompt_content': prompt_content,
                        'file': file_path,
                        'position': match.start(),
                        'suggested_yaml': self._generate_yaml_template(template_name, prompt_content)
                    })
        
        except Exception as e:
            logger.error(f"Error extracting prompts from {file_path}: {e}")
        
        return extracted_prompts
    
    def _generate_template_name(self, file_path: str, position: int, content: str) -> str:
        """Generate a template name based on file context"""
        # Extract function name if possible
        lines_before = content[:position].split('\n')
        function_name = None
        
        for line in reversed(lines_before):
            if 'def ' in line and '(' in line:
                function_name = line.split('def ')[1].split('(')[0].strip()
                break
        
        # Generate template name
        file_stem = Path(file_path).stem
        if function_name:
            return f"{file_stem}_{function_name}"
        else:
            return f"{file_stem}_prompt"
    
    def _generate_yaml_template(self, template_name: str, prompt_content: str) -> str:
        """Generate YAML template from extracted prompt"""
        return f"""
{template_name}:
  description: "Auto-extracted prompt from code"
  category: "extracted"
  latest_version: "v1.0"
  versions:
    v1.0:
      system_message: "You are an expert AI assistant."
      prompt: |
{prompt_content}
      parameters:
        temperature: 0.7
        max_tokens: 1000
"""


# Example usage and testing
if __name__ == "__main__":
    # Test the governance system
    try:
        governance = PromptGovernance()
        
        # Run governance checks
        summary = governance.enforce_prompt_standards()
        print(f"Governance Summary: {summary}")
        
        # Get violations
        violations = governance.scan_for_hardcoded_prompts()
        print(f"Found {len(violations)} violations")
        
        # Suggest fixes
        if violations:
            fixes = governance.suggest_fixes(violations)
            print(f"Suggested {len(fixes)} fixes")
        
        print("✅ PromptGovernance test successful")
        
    except Exception as e:
        print(f"❌ Error testing PromptGovernance: {e}")
