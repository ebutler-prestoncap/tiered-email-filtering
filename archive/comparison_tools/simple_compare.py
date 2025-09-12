import pandas as pd

# Read files
tiered_df = pd.read_excel('output/Two_Tier_Filtered_Family_Office_Contacts_v6.xlsx')
original_df = pd.read_excel('../email-filtering-tool/output/Filtered_Out_Contacts.xlsx')

print(f"Tiered: {tiered_df.shape[0]} contacts")
print(f"Original: {original_df.shape[0]} contacts")

# Compare contact IDs
tiered_ids = set(tiered_df['CONTACT_ID'].astype(str))
original_ids = set(original_df['CONTACT_ID'].astype(str))

diff = tiered_ids - original_ids
print(f"Contacts in tiered but not original: {len(diff)}")

# Get details for different contacts
missing_contacts = tiered_df[tiered_df['CONTACT_ID'].astype(str).isin(diff)]

if len(missing_contacts) > 0:
    print("\nContacts not in original filtering:")
    for idx, row in missing_contacts.iterrows():
        print(f"ID: {row['CONTACT_ID']}, Name: {row['NAME']}, Investor: {row['INVESTOR']}, Email: {row['EMAIL']}")
else:
    print("No differences found")
