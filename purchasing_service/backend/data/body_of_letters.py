def completing_registration(token: str) -> str:
    return f"""
    Hello!
    You have received this message because your email address was specified for user registration on our Compraretis service.
    If it wasn't You who tried to register, then ignore this message.
    Your personal code: 
       {token} 
    Don't forget to send a POST request to complete the registration by specifying the email address and code in the token field.
    
    Your service for Compraretis orders.
    """
