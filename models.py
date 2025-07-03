from database import Base
from sqlalchemy import Column, Integer, BigInteger, String, Text, Date, DateTime, Boolean, ForeignKey, func

class Certifications(Base):
    __tablename__ = "certifications"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    image = Column(String(255), nullable=False)
    certificate_name = Column(String(255), nullable=False)
    year = Column(Integer, nullable=False)
    type = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )


class Countries(Base):
    __tablename__ = "countries"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    abbreviation = Column(String(255))
    currency = Column(String(255))
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )
    code = Column(String(255))


class Departments(Base):
    __tablename__ = "departments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    faculty_id = Column(BigInteger, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )


class ExecutiveComittes(Base):
    __tablename__ = "executive_comittes"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    photo = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    position = Column(String(255), nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )


class Faculties(Base):
    __tablename__ = "faculties"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )


class FailedJobs(Base):
    __tablename__ = "failed_jobs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    uuid = Column(String(255), nullable=False)
    connection = Column(Text, nullable=False)
    queue = Column(Text, nullable=False)
    payload = Column(Text, nullable=False)
    exception = Column(Text, nullable=False)
    failed_at = Column(DateTime, nullable=False)


class Jobs(Base):
    __tablename__ = "jobs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    queue = Column(String(255), nullable=False)
    payload = Column(Text, nullable=False)
    attempts = Column(Boolean, nullable=False)
    reserved_at = Column(Integer)
    available_at = Column(Integer, nullable=False)
    created_at = Column(Integer, nullable=False)


class LatestNews(Base):
    __tablename__ = "latest_news"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    date = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    photo = Column(String(255), nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )


class Migrations(Base):
    __tablename__ = "migrations"

    # mark `id` as the primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    migration = Column(String(255), nullable=False)
    batch = Column(Integer, nullable=False)


class Opportunities(Base):
    __tablename__ = "opportunities"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    photo = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    date = Column(Date, nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )
    user_id = Column(Integer)
    status = Column(String(255))
    link = Column(Text)


class OpportunityHistories(Base):
    __tablename__ = "opportunity_histories"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    opportunity_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    comment = Column(Text, nullable=False)
    status = Column(String(255), nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )


class PasswordResets(Base):
    __tablename__ = "password_resets"

    email = Column(String(255), primary_key=True, nullable=False)
    token = Column(String(255), primary_key=True, nullable=False)
    created_at = Column(DateTime)


class PersonalAccessTokens(Base):
    __tablename__ = "personal_access_tokens"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tokenable_type = Column(String(255), nullable=False)
    tokenable_id = Column(BigInteger, nullable=False)
    name = Column(String(255), nullable=False)
    token = Column(String(64), nullable=False)
    abilities = Column(Text)
    last_used_at = Column(DateTime)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )


class PersonalInformation(Base):
    __tablename__ = "personal_information"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    photo = Column(String(255), nullable=True)
    bio = Column(Text, nullable=False)
    current_employer = Column(String(255))
    self_employed = Column(String(255))
    latest_education_level = Column(String(255))
    address = Column(String(255), nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )
    profession_id = Column(Integer)
    user_id = Column(Integer)
    dob = Column(Date)
    start_date = Column(Date)
    end_date = Column(Date)
    faculty_id = Column(BigInteger)
    country_id = Column(String(255))
    department = Column(String(255))
    gender = Column(Boolean, nullable=False)
    status = Column(String(255))


class Professions(Base):
    __tablename__ = "professions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )


class Programs(Base):
    __tablename__ = "programs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    photo = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(255), nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )


class ProgramAttendances(Base):
    __tablename__ = "program_attendances"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    names = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone_number = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )


class Sliders(Base):
    __tablename__ = "sliders"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    photo = Column(String(255))
    description = Column(Text)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )


class SocialActivities(Base):
    __tablename__ = "social_activities"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    photo = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(255), nullable=False)
    date = Column(Date, nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )


class Students(Base):
    __tablename__ = "students"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    id_number = Column(Integer, nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )


class SubscribedUsers(Base):
    __tablename__ = "subscribed_users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False)
    token = Column(String(255))
    status = Column(String, nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )


class UpComingEvents(Base):
    __tablename__ = "up_coming_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    photo = Column(String(255), nullable=False)
    date = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )


class Users(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False)
    email_verified_at = Column(DateTime)
    password = Column(String(255), nullable=False)
    remember_token = Column(String(100))
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )
    first_name = Column(String(255))
    last_name = Column(String(255))
    phone_number = Column(String(255))
    is_staff = Column(Boolean)
    student_id = Column(Integer, nullable=False)
    type = Column(String(255))


class WorkExperiences(Base):
    __tablename__ = "work_experiences"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    company = Column(String(255), nullable=False)
    employer = Column(String(255), nullable=False)
    job_title = Column(String(255), nullable=False)
    job_description = Column(Text, nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )
    start_date = Column(Date, nullable=False)
    end_date = Column(String(255))
    user_id = Column(Integer)

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    id = Column(Integer, primary_key=True, autoincrement=True)
    jti = Column(String(36), unique=True, nullable=False)
    revoked_at = Column(DateTime, nullable=False, server_default=func.now())

class Discussions(Base):
    """
    Stores one message per row in a free-form discussion thread.

    Fields
    ------
    id          : primary-key (bigint, auto-increment)
    user_id     : ID of the authoring user  ➜  FK → users.id  (no cascade in ORM)
    message     : the message body
    created_at  : timestamp (server-side default = NOW)
    """
    __tablename__ = "discussions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )