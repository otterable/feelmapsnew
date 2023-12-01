import qrcode

# Define the OTP secret and the issuer name
otp_secret = "MangoOttersLove"
issuer_name = "Stimmungskompass"
username = "admin"

# Create the otpauth URL
otpauth_url = f"otpauth://totp/{issuer_name}:{username}?secret={otp_secret}&issuer={issuer_name}"

# Generate QR code
img = qrcode.make(otpauth_url)

# Save the QR code or display it
img.save("otp_secret_qr.png")
img.show()
