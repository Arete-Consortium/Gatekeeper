#!/usr/bin/env bash
# Setup Fly.io secrets for EVE Gatekeeper
# Run this after obtaining your API keys.
#
# Usage:
#   ./scripts/setup-secrets.sh

set -euo pipefail
export PATH="$HOME/.fly/bin:$PATH"
APP="eve-gatekeeper"

echo "=== EVE Gatekeeper — Production Secrets Setup ==="
echo ""

# ---------- ESI OAuth ----------
echo "--- Step 1: ESI OAuth ---"
echo "Register at: https://developers.eveonline.com/applications"
echo "  App name:     EVE Gatekeeper"
echo "  Callback URL: https://eve-gatekeeper.fly.dev/api/v1/auth/callback"
echo "  Scopes:       esi-location.read_location.v1"
echo "                esi-location.read_ship_type.v1"
echo "                esi-ui.write_waypoint.v1"
echo ""
read -rp "ESI Client ID: " ESI_CLIENT_ID
read -rp "ESI Secret Key: " ESI_SECRET_KEY

if [[ -n "$ESI_CLIENT_ID" && -n "$ESI_SECRET_KEY" ]]; then
  flyctl secrets set \
    ESI_CLIENT_ID="$ESI_CLIENT_ID" \
    ESI_SECRET_KEY="$ESI_SECRET_KEY" \
    ESI_CALLBACK_URL="https://eve-gatekeeper.fly.dev/api/v1/auth/callback" \
    -a "$APP"
  echo "✓ ESI secrets set"
else
  echo "⏭ Skipped ESI (empty input)"
fi

echo ""

# ---------- Stripe ----------
echo "--- Step 2: Stripe Billing ---"
echo "Get keys at: https://dashboard.stripe.com/apikeys"
echo "Create a webhook at: https://dashboard.stripe.com/webhooks"
echo "  Endpoint URL: https://eve-gatekeeper.fly.dev/api/v1/billing/webhook"
echo "  Events:       checkout.session.completed"
echo "                customer.subscription.updated"
echo "                customer.subscription.deleted"
echo ""
read -rp "Stripe Secret Key (sk_...): " STRIPE_SECRET_KEY
read -rp "Stripe Webhook Secret (whsec_...): " STRIPE_WEBHOOK_SECRET
read -rp "Stripe Pro Price ID (price_...): " STRIPE_PRO_MONTHLY_PRICE_ID

if [[ -n "$STRIPE_SECRET_KEY" ]]; then
  flyctl secrets set \
    STRIPE_SECRET_KEY="$STRIPE_SECRET_KEY" \
    STRIPE_WEBHOOK_SECRET="${STRIPE_WEBHOOK_SECRET:-}" \
    STRIPE_PRO_MONTHLY_PRICE_ID="${STRIPE_PRO_MONTHLY_PRICE_ID:-}" \
    -a "$APP"
  echo "✓ Stripe secrets set"
else
  echo "⏭ Skipped Stripe (empty input)"
fi

echo ""
echo "=== Done ==="
echo "Current secrets:"
flyctl secrets list -a "$APP"
