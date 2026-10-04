def settle_up(totals, payer):
    """
    Calculates settlement payments given per-person totals and the payer.
    Returns a list of (debtor, creditor, amount) tuples.
    """
    if not payer or payer not in totals:
        return []
    payments = []
    for person, amount in totals.items():
        if person != payer and amount > 0:
            payments.append((person, payer, round(amount, 2)))
    return payments
