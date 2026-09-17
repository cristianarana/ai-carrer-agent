from ..interfaces.candidate_profile import CandidateProfile


def validate(profile: CandidateProfile) -> None:
    if profile.name is not None and len(profile.name) < 2:
        raise ValueError(
            f"CANDIDATE_PROFILE.name must have at least 2 characters, got "
            f"'{profile.name}'"
        )