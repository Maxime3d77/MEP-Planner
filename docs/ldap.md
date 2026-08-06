# LDAP / Active Directory

Open **Administration → LDAP / AD**. Configure the directory URL, bind account, user base DN, login attribute, group base DN and role mappings. Keep TLS certificate verification enabled. Import the internal CA certificate when LDAPS uses a private PKI.


## Individually imported users

Users imported from **Settings → Users → Import from LDAP** are explicitly authorized in MEP Planner and can authenticate even when they do not belong to a mapped LDAP group. Their MEP Planner role is the role selected during import. Just-In-Time users remain subject to LDAP group mappings.
