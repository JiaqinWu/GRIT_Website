# Streamlit Cloud Setup Instructions

## Adding Secrets to Streamlit Cloud

When deploying to Streamlit Cloud, you need to add your secrets through the dashboard (not via the secrets.toml file).

### Steps:

1. Go to your Streamlit Cloud dashboard: https://share.streamlit.io/
2. Navigate to your app settings
3. Click on "Secrets" or "Advanced settings"
4. Add the following secrets structure:

```toml
[users."JWu@pwcgov.org"]
[users."JWu@pwcgov.org".GRIT]
password = "Qin88251216"
name = "Jiaqin Wu"

[users."JWu@pwcgov.org".IPE]
password = "Qin88251216"
name = "Jiaqin Wu"

[users."TYasin1@pwcgov.org"]
[users."TYasin1@pwcgov.org".GRIT]
password = "TYasin1"
name = "Tauheeda Martin Yasin"

[users."TYasin1@pwcgov.org".IPE]
password = "TYasin1"
name = "Tauheeda Martin Yasin"

[users."jkooyoomjian@pwcgov.org"]
[users."jkooyoomjian@pwcgov.org".GRIT]
password = "jkooyoomjian"
name = "Jennifer Kooyoomijian"

[users."jkooyoomjian@pwcgov.org".IPE]
password = "jkooyoomjian"
name = "Jennifer Kooyoomiji"
```

5. Make sure you also have your other secrets configured:
   - `gcp_service_account` (for Google Sheets access)
   - `mailjet` (for email functionality)

6. Save and redeploy your app

### Note:
- The secrets.toml file is only used for local development
- Streamlit Cloud uses the secrets from the dashboard, not from files
- Never commit secrets.toml to your repository (it's in .gitignore)

