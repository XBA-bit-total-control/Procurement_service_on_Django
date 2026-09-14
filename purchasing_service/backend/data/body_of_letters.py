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


def change_email_for_now(token: str) -> str:
    return f"""
    Your email address on the Compraretis service has been changed, and your profile is now unverified again.
    To continue using the service, please verify the new email address by accessing the resource api/v1/user/register/confirm
    Your personal code {token}
    
    Sincerely, the Compraretis order service.
    """


def change_email_for_old(admin_email: str) -> str:
    return f"""
    The email address in your profile on the Compraretis service has been changed.
    If you didn’t do this, please contact the administrator at {admin_email}
    
    Sincerely, the Compraretis order service.
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


def shop_registration(
        first_name: str,
        token: str,
        link_to_agreement: str
) -> str:
    return f"""
    {first_name} we are very glad that You wanted to cooperate with us.
    Before becoming our partner and starting to sell your products, please read the partnership agreement {link_to_agreement}.
    If You agree with it, to complete the registration of your store, send the token via the POST api/v1/partner/register/confirm resource.
    Your personal code is {token}
    
    Your service for Compraretis orders.
    """
