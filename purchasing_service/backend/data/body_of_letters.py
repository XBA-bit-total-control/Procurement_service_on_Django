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


def order_created_for_user(
        order_id: int,
        order_price: float,
        username: str
) -> str:
    return f"""
    {username.capitalize()} hello!
    Your order for the amount of {order_price} rubles has been accepted for processing and has the number {order_id}
    Thank you for your purchase!
    """


def order_created_for_admin(
        order_id: int,
        order_price: float,
        username: str,
        user_id: int
) -> str:
    return f"""
    The user {username} with id={user_id} wants to place an order with order id={order_id} for the amount {order_price}
    Confirmation is required.
    """
