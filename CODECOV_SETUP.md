# Codecov Setup Instructions

To enable the coverage badge in README, you need to add a `CODECOV_TOKEN` secret to GitHub.

## Steps

### 1. Sign up for Codecov (Free)

Visit: https://codecov.io/

- Click "Sign up with GitHub"
- Authorize Codecov to access your repositories
- Select "FlockParser" repository

### 2. Get Your Token

1. Go to: https://codecov.io/gh/BenevolentJoker-JohnL/FlockParser
2. Click "Settings" → "General"
3. Copy the "Repository Upload Token"

### 3. Add Token to GitHub Secrets

1. Go to your GitHub repo: https://github.com/BenevolentJoker-JohnL/FlockParser
2. Click "Settings" → "Secrets and variables" → "Actions"
3. Click "New repository secret"
4. Name: `CODECOV_TOKEN`
5. Value: Paste the token from step 2
6. Click "Add secret"

### 4. Verify

1. Push a commit to trigger CI
2. Check the Actions tab - coverage should upload automatically
3. Wait ~1 minute, then refresh the README
4. The Codecov badge should show your coverage percentage

## Expected Result

Badge will change from:
```
codecov: unknown
```

To:
```
codecov: 42%
```

(Actual coverage will vary based on your test suite)

## Troubleshooting

### Badge still shows "unknown"

- Check GitHub Actions logs for upload errors
- Verify the secret name is exactly `CODECOV_TOKEN`
- Make sure you're pushing to `main` branch (CI only runs on main/develop)

### Coverage seems low

This is expected! Current test coverage is ~40%. See KNOWN_ISSUES.md for roadmap:
- v1.1.0 target: 60% coverage
- v1.2.0 target: 80% coverage

The badge is honest - it shows real coverage, not aspirational numbers.
