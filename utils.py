def validate_file_type(filename, allowed_types):
    '''
    Check if the file type is valid.
    Allowed types must be an array
    '''
    return filename.split(".")[-1] in allowed_types


def _send_email_to_all(User, mail, Message, jsonify, subject, message):
    users = User.query.all()

    with mail.connect() as conn:
        for user in users:
            msg = Message(recipients=[user.email],
                          body=message,
                          subject=subject)

            conn.send(msg)

    return jsonify("send to all")


def _send_email(User, EMAIL, Message, mail, jsonify, subject, message):
    user = User.query.filter_by(email=EMAIL).first()

    msg = Message(subject, recipients=[user.email])
    msg.body = message
    mail.send(msg)

    return jsonify("send to test")


def _send_targeted_email(users, mail, Message, jsonify, subject, email_content):
    msg = Message(subject, recipients=[user.email for user in users])
    msg.body = email_content
    mail.send(msg)

    return jsonify("send targeted")
