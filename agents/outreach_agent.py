from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from agents.models import CarPreferences, CarListing
from config import LLM_MODEL, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
from config import SENDGRID_API_KEY, SENDGRID_FROM_EMAIL
import json


_EMAIL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are an expert automotive assistant writing a personalized car search results email. Be professional, clear, and helpful."),
    ("human", (
        "Write an HTML email body for these top car listings found for {name}.\n"
        "Preferences: {make} {model}, budget ${price_min:,}-${price_max:,}, near {location}.\n\n"
        "Top listings:\n{listings_json}\n\n"
        "Include: greeting, listing summaries (price, mileage, color, dealer, link), and a call to action."
    )),
])

_SMS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Write a concise SMS under 300 characters. Include top 1-3 cars with price and mileage. End with a call to action."),
    ("human", (
        "SMS summary for {make} {model} search near {location}:\n{listings_json}"
    )),
])


def generate_email_content(prefs: CarPreferences, listings: list[CarListing]) -> str:
    llm = ChatOpenAI(model=LLM_MODEL, temperature=0.4)
    chain = _EMAIL_PROMPT | llm | StrOutputParser()
    listings_data = [l.model_dump() for l in listings]
    return chain.invoke({
        "name": prefs.user_email or "Car Buyer",
        "make": prefs.make,
        "model": prefs.model,
        "price_min": prefs.price_min,
        "price_max": prefs.price_max,
        "location": prefs.location,
        "listings_json": json.dumps(listings_data, indent=2),
    })


def generate_sms_content(prefs: CarPreferences, listings: list[CarListing]) -> str:
    llm = ChatOpenAI(model=LLM_MODEL, temperature=0.3)
    chain = _SMS_PROMPT | llm | StrOutputParser()
    top3 = [l.model_dump() for l in listings[:3]]
    return chain.invoke({
        "make": prefs.make,
        "model": prefs.model,
        "location": prefs.location,
        "listings_json": json.dumps(top3, indent=2),
    })


def send_sms(to_number: str, message: str) -> dict:
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to_number,
        )
        return {"success": True, "sid": msg.sid}
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_email(to_email: str, subject: str, html_body: str) -> dict:
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail
        sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
        mail = Mail(
            from_email=SENDGRID_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html_body,
        )
        response = sg.send(mail)
        return {"success": True, "status": response.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_outreach_agent(prefs: CarPreferences, listings: list[CarListing]) -> dict:
    results = {}

    if prefs.delivery_email and prefs.user_email:
        email_body = generate_email_content(prefs, listings)
        subject = f"Your {prefs.make} {prefs.model} Results - Top {len(listings)} Picks"
        results["email"] = send_email(prefs.user_email, subject, email_body)
        results["email_content"] = email_body

    if prefs.delivery_sms and prefs.user_phone:
        sms_body = generate_sms_content(prefs, listings)
        results["sms"] = send_sms(prefs.user_phone, sms_body)
        results["sms_content"] = sms_body

    return results
