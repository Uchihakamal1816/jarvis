"""
JARVIS Core — Policy and Permissions
Guards sensitive actions and enforces approval requirements.
"""

import logging

log = logging.getLogger(__name__)

class PermissionManager:
    def __init__(self):
        # Default policies for critical actions
        self.policies = {
            "delete_file": "requires_approval",
            "send_email": "requires_approval",
            "purchase": "requires_approval",
            "read_file": "allow",
            "search_web": "allow"
        }
        
    def check_permission(self, action: str) -> str:
        """
        Returns 'allow', 'requires_approval', or 'deny'.
        """
        policy = self.policies.get(action, "requires_approval")
        log.debug("Policy check for action '%s': %s", action, policy)
        return policy

permission_manager = PermissionManager()
