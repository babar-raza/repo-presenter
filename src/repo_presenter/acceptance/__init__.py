"""Acceptance-calibration support: the A1 held-out registration and its successors.

This package holds the *selection logic* used to build the held-out acceptance registration
"A1" (see ``registration.py``). It never writes the committed registration file itself; that is
a supervisor-direct follow-up once the module is accepted (see ``registration.py``'s module
docstring and TC-022a's ``closeout``).
"""
