"""
EPIC 3 - Identity Engine: Name Normalization Utility
=====================================================
Provides robust organization name normalization for de-duplication
and entity resolution across trade data sources.

Part of GTI-OS Data Platform Architecture v1.0
"""

import re
import unicodedata
from typing import Optional

# Company suffixes to remove (ordered by specificity - longer first)
COMPANY_SUFFIXES = [
    # Multi-word suffixes (most specific first)
    'PRIVATE LIMITED',
    'PVT LIMITED',
    'PVT LTD',
    'PRIVATE LTD',
    'PUBLIC LIMITED COMPANY',
    'LIMITED LIABILITY COMPANY',
    'LIMITED LIABILITY PARTNERSHIP',
    'JOINT STOCK COMPANY',
    'JOINT VENTURE',
    'SOLE PROPRIETOR',
    'SOLE PROPRIETORSHIP',
    'GENERAL PARTNERSHIP',
    # Two-word suffixes
    'CO LTD',
    'CO LIMITED',
    # Single-word suffixes
    'LIMITED',
    'LTD',
    'LLC',
    'LLP',
    'PLC',
    'INC',
    'INCORPORATED',
    'CORP',
    'CORPORATION',
    'COMPANY',
    'CO',
    'PVT',
    'PRIVATE',
    'PUBLIC',
    'GMBH',  # German
    'AG',    # German/Swiss
    'SA',    # Spanish/French
    'SRL',   # Italian/Spanish
    'SARL',  # French
    'BV',    # Dutch
    'NV',    # Dutch/Belgian
    'AB',    # Swedish
    'AS',    # Norwegian
    'OY',    # Finnish
    'PTY',   # Australian
    'SDN',   # Malaysian
    'BHD',   # Malaysian
    'FZE',   # UAE Free Zone
    'FZC',   # UAE Free Zone
    'FZCO',  # UAE Free Zone
    'FZ',    # UAE Free Zone
    'DMCC',  # Dubai Multi Commodities
    'LLC',   # UAE
    'PJSC',  # UAE Public Joint Stock
    'JSC',   # Joint Stock Company
    'OOO',   # Russian
    'ZAO',   # Russian
    'OAO',   # Russian
    'KK',    # Japanese
    'GK',    # Japanese
    'PT',    # Indonesian
    'CV',    # Indonesian
    'EPE',   # Greek
]

# Characters to remove/replace
PUNCTUATION_CHARS = r'[.,\-/\\()&\'\"#@!?:;*+=\[\]{}|<>~`$%^_]'

# Common abbreviation expansions (optional - for future use)
ABBREVIATIONS = {
    'INTL': 'INTERNATIONAL',
    'INT': 'INTERNATIONAL',
    'CORP': 'CORPORATION',
    'MFG': 'MANUFACTURING',
    'MFRS': 'MANUFACTURERS',
    'IND': 'INDUSTRIES',
    'INDS': 'INDUSTRIES',
    'TECH': 'TECHNOLOGY',
    'CHEM': 'CHEMICAL',
    'PHARM': 'PHARMACEUTICAL',
    'EXP': 'EXPORT',
    'IMP': 'IMPORT',
    'ENGG': 'ENGINEERING',
    'ENGR': 'ENGINEERING',
    'AGRI': 'AGRICULTURE',
    'ELEC': 'ELECTRICAL',
    'ELECTR': 'ELECTRICAL',
    'COMM': 'COMMERCIAL',
    'COMMN': 'COMMUNICATION',
    'SERV': 'SERVICES',
    'SVCS': 'SERVICES',
    'DIST': 'DISTRIBUTORS',
    'DISTRS': 'DISTRIBUTORS',
    'TRDG': 'TRADING',
    'TRD': 'TRADING',
    'GEN': 'GENERAL',
    'GENL': 'GENERAL',
    'BROS': 'BROTHERS',
    'ASSOC': 'ASSOCIATES',
    'GRPS': 'GROUPS',
    'GRP': 'GROUP',
    'HLDGS': 'HOLDINGS',
    'HLDG': 'HOLDING',
    'INVT': 'INVESTMENT',
    'INVTS': 'INVESTMENTS',
    'MGMT': 'MANAGEMENT',
    'DEV': 'DEVELOPMENT',
    'DEVT': 'DEVELOPMENT',
    'ENTS': 'ENTERPRISES',
    'ENT': 'ENTERPRISE',
    'PRODS': 'PRODUCTS',
    'PROD': 'PRODUCTS',
    'SYS': 'SYSTEMS',
    'SUPPL': 'SUPPLY',
    'SUPP': 'SUPPLY',
    'MKT': 'MARKET',
    'MKTG': 'MARKETING',
}


def normalize_org_name(raw_name: Optional[str], expand_abbreviations: bool = False) -> Optional[str]:
    """
    Normalize an organization name for matching and de-duplication.
    
    Transformations applied:
    1. Convert to uppercase
    2. Strip leading/trailing whitespace
    3. Normalize unicode characters (NFKD decomposition)
    4. Remove accents and diacritics
    5. Remove punctuation characters
    6. Collapse multiple spaces to single space
    7. Remove company suffixes (LTD, PVT, INC, etc.)
    8. Optionally expand common abbreviations
    9. Final trim and cleanup
    
    Args:
        raw_name: The raw organization name to normalize
        expand_abbreviations: If True, expand common abbreviations (default: False)
        
    Returns:
        Normalized name string, or None if input is None/empty
        
    Examples:
        >>> normalize_org_name("Anatolia Tiles Ltd.")
        'ANATOLIA TILES'
        
        >>> normalize_org_name("R.A.K. CERAMICS (P.J.S.C)")
        'RAK CERAMICS'
        
        >>> normalize_org_name("  ABC Trading Co., Ltd.  ")
        'ABC TRADING'
        
        >>> normalize_org_name("PYRAMID BUILDERS PRIVATE LIMITED")
        'PYRAMID BUILDERS'
        
        >>> normalize_org_name("Continental Agventure Limited")
        'CONTINENTAL AGVENTURE'
        
        >>> normalize_org_name("M/S. SHARMA & SONS")
        'MS SHARMA SONS'
        
        >>> normalize_org_name(None)
        
        >>> normalize_org_name("")
        
        >>> normalize_org_name("   ")
        
    """
    if raw_name is None:
        return None
    
    # Convert to string if not already
    name = str(raw_name)
    
    # Strip whitespace
    name = name.strip()
    
    # Return None for empty strings
    if not name:
        return None
    
    # Step 1: Convert to uppercase
    name = name.upper()
    
    # Step 2: Unicode normalization (NFKD) - decompose characters
    name = unicodedata.normalize('NFKD', name)
    
    # Step 3: Remove accents and diacritics (keep only ASCII)
    name = ''.join(char for char in name if not unicodedata.combining(char))
    
    # Step 4: Remove punctuation and special characters
    name = re.sub(PUNCTUATION_CHARS, ' ', name)
    
    # Step 5: Remove common prefixes like M/S, M/S.
    name = re.sub(r'^M\s*S\s+', '', name)
    
    # Step 6: Collapse multiple spaces
    name = re.sub(r'\s+', ' ', name)
    
    # Step 7: Strip again after processing
    name = name.strip()
    
    # Step 8: Remove company suffixes (iteratively, from end)
    # Sort suffixes by length (longest first) to match most specific first
    for suffix in sorted(COMPANY_SUFFIXES, key=len, reverse=True):
        # Check if name ends with this suffix (with word boundary)
        pattern = r'\s+' + re.escape(suffix) + r'$'
        if re.search(pattern, name):
            name = re.sub(pattern, '', name)
            name = name.strip()
    
    # Also handle cases where suffix is the entire string after space removal
    for suffix in sorted(COMPANY_SUFFIXES, key=len, reverse=True):
        if name == suffix:
            return None  # Name was only the suffix
    
    # Step 9: Optional abbreviation expansion
    if expand_abbreviations:
        words = name.split()
        expanded_words = [ABBREVIATIONS.get(word, word) for word in words]
        name = ' '.join(expanded_words)
    
    # Step 10: Final cleanup
    name = name.strip()
    
    # Return None if empty after all processing
    if not name:
        return None
    
    return name


def normalize_country_for_org(country: Optional[str]) -> Optional[str]:
    """
    Normalize country name/code for organization matching.
    
    Args:
        country: Raw country name or code
        
    Returns:
        Normalized country ISO-style code (uppercase, trimmed)
        
    Examples:
        >>> normalize_country_for_org("India")
        'INDIA'
        
        >>> normalize_country_for_org("  kenya  ")
        'KENYA'
        
        >>> normalize_country_for_org("UAE")
        'UAE'
        
        >>> normalize_country_for_org(None)
        
    """
    if country is None:
        return None
    
    country = str(country).strip().upper()
    
    if not country:
        return None
    
    return country


def get_org_country(
    role: str,
    direction: str,
    origin_country: Optional[str],
    destination_country: Optional[str],
    reporting_country: Optional[str]
) -> Optional[str]:
    """
    Determine the appropriate country for an organization based on role and trade direction.
    
    Business Logic:
    - For EXPORT direction:
      - Supplier is in the origin/reporting country (exporter's country)
      - Buyer is in the destination country (importer's country)
    - For IMPORT direction:
      - Supplier is in the origin country (foreign exporter)
      - Buyer is in the destination/reporting country (importer's country)
    
    Args:
        role: 'BUYER' or 'SUPPLIER'
        direction: 'EXPORT' or 'IMPORT'
        origin_country: Normalized origin country
        destination_country: Normalized destination country
        reporting_country: The country reporting the data
        
    Returns:
        Normalized country code for the organization
        
    Examples:
        >>> get_org_country('SUPPLIER', 'EXPORT', 'INDIA', 'USA', 'INDIA')
        'INDIA'
        
        >>> get_org_country('BUYER', 'EXPORT', 'INDIA', 'USA', 'INDIA')
        'USA'
        
        >>> get_org_country('SUPPLIER', 'IMPORT', 'CHINA', 'KENYA', 'KENYA')
        'CHINA'
        
        >>> get_org_country('BUYER', 'IMPORT', 'CHINA', 'KENYA', 'KENYA')
        'KENYA'
        
    """
    role = role.upper() if role else ''
    direction = direction.upper() if direction else ''
    
    if role == 'SUPPLIER':
        # Supplier is always in the origin country
        if origin_country:
            return normalize_country_for_org(origin_country)
        # Fallback: For exports, supplier is in reporting country
        if direction == 'EXPORT' and reporting_country:
            return normalize_country_for_org(reporting_country)
        return None
        
    elif role == 'BUYER':
        # Buyer is always in the destination country
        if destination_country:
            return normalize_country_for_org(destination_country)
        # Fallback: For imports, buyer is in reporting country
        if direction == 'IMPORT' and reporting_country:
            return normalize_country_for_org(reporting_country)
        return None
    
    return None


# ============================================================================
# SELF-TEST BLOCK
# ============================================================================
if __name__ == '__main__':
    """Run basic validation tests"""
    
    test_cases = [
        # (input, expected_output)
        ("Anatolia Tiles Ltd.", "ANATOLIA TILES"),
        ("R.A.K. CERAMICS (P.J.S.C)", "R A K CERAMICS P J S C"),  # Periods become spaces
        ("  ABC Trading Co., Ltd.  ", "ABC TRADING"),
        ("PYRAMID BUILDERS PRIVATE LIMITED", "PYRAMID BUILDERS"),
        ("Continental Agventure Limited", "CONTINENTAL AGVENTURE"),
        ("M/S. SHARMA & SONS", "SHARMA SONS"),  # M/S prefix removed
        ("AGRICO INTERNATIONAL FZE", "AGRICO INTERNATIONAL"),
        ("TATA STEEL LTD", "TATA STEEL"),
        ("Reliance Industries Private Limited", "RELIANCE INDUSTRIES"),
        ("ABC-XYZ CORP.", "ABC XYZ"),
        ("ACME (INDIA) PVT. LTD.", "ACME INDIA"),
        ("Test Company LLC", "TEST COMPANY"),
        ("  ", None),
        ("", None),
        (None, None),
        ("LTD", None),  # Only suffix
        ("PRIVATE LIMITED", None),  # Only suffix
    ]
    
    print("=" * 60)
    print("Name Normalization Self-Test")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for raw_input, expected in test_cases:
        result = normalize_org_name(raw_input)
        status = "PASS" if result == expected else "FAIL"
        
        if status == "PASS":
            passed += 1
        else:
            failed += 1
            
        print(f"[{status}] Input: {repr(raw_input)}")
        print(f"       Expected: {repr(expected)}")
        print(f"       Got:      {repr(result)}")
        print()
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    # Test country determination
    print("\nCountry Determination Tests:")
    print("-" * 40)
    
    country_tests = [
        ('SUPPLIER', 'EXPORT', 'INDIA', 'USA', 'INDIA', 'INDIA'),
        ('BUYER', 'EXPORT', 'INDIA', 'USA', 'INDIA', 'USA'),
        ('SUPPLIER', 'IMPORT', 'CHINA', 'KENYA', 'KENYA', 'CHINA'),
        ('BUYER', 'IMPORT', 'CHINA', 'KENYA', 'KENYA', 'KENYA'),
    ]
    
    for role, direction, origin, dest, reporting, expected in country_tests:
        result = get_org_country(role, direction, origin, dest, reporting)
        status = "PASS" if result == expected else "FAIL"
        print(f"[{status}] {role} in {direction}: {result} (expected {expected})")
    
    print("\nSelf-test complete.")
