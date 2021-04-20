from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired


class MoveForm(FlaskForm):
    move = StringField('Вводите 4 цифры', validators=[DataRequired()])
    submit = SubmitField('Подтверждаю ход')
