EMAIL_TEMPLATE = "email.html"


def validate_file_type(filename, allowed_types):
    '''
    Check if the file type is valid.
    Allowed types must be an array
    '''
    return filename.split(".")[-1] in allowed_types


def _send_email_to_all(User, mail, Message, jsonify, subject, message, r_t):
    users = User.query.all()

    with mail.connect() as conn:
        for user in users:
            if type(message) is dict:
                message['user'] = user
                msg = Message(recipients=[user.email],
                              html=r_t(EMAIL_TEMPLATE, **message),
                              subject=subject)
            else:
                message['user'] = user
                msg = Message(recipients=[user.email],
                              body=message,
                              subject=subject)

            conn.send(msg)

    return jsonify("send to all")


def _send_email(User, EMAIL, Message, mail, jsonify, subject, email_content):
    user = User.query.filter_by(email=EMAIL).first()
    message['user'] = user

    msg = Message(subject, recipients=[user.email])
    msg.body = email_content
    mail.send(msg)

    return jsonify("send to test")


def _send_targeted_email(users, mail, Message, jsonify, subject, message, r_t):
    with mail.connect() as conn:
        for user in users:
            message['user'] = user
            msg = Message(recipients=[user.email],
                          html=r_t(EMAIL_TEMPLATE, **message),
                          subject=subject)

            conn.send(msg)

    return jsonify("send targeted")
