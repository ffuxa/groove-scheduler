import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple
from copy import deepcopy

# Global constants
TIMESTEP: timedelta = timedelta(minutes=30)


class Student:
    """Represents a student (groover) who has filled out their avails"""
    def __init__(self, name: str):
        self.name: str = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, Student):
            return self.name == other.name
        return NotImplemented


class Availability:
    """Used to a mapping between a specific time and who is available at said time"""
    def __init__(self, availability: Dict[datetime, List[Student]]):
        self.avails_dict: Dict[datetime, List[Student]] = availability
        print(self.avails_dict.keys())

    def __str__(self):
        return str({k.strftime('%Y-%m-%d %H:%M:%S'): v for k, v in self.avails_dict.items()})


class Song:
    def __init__(self, name: str, leader: Student, members: List[Student],
                 practice_length: timedelta = timedelta(hours=1)):
        self.name: str = name
        self.leader: Student = leader
        self.members: List[Student] = members
        self.practice_length: timedelta = practice_length

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, Song):
            return self.name == other.name
        return NotImplemented


class Schedule:
    def __init__(self):
        self.song_order: List[Song] = []
        self.cost = None

    def __str__(self):
        return str(self.song_order)

    def __repr__(self):
        return str(self.song_order)


def get_whenisgood_availability(event_id: str,
                                response_code: str) -> Tuple[List[Student], Availability]:
    """
    Scrapes the html of when is good to get student availability.
    Source: https://github.com/yknot/WhenIsGoodScraper/
    """
    # get results page
    r = requests.get('http://whenisgood.net/{}/results/{}'.format(event_id,
                                                                  response_code))
    soup = BeautifulSoup(r.text, "html.parser")
    # get the script at the bottom
    raw = soup.find_all('script')[-1].text.splitlines()
    # filter out beginning and end rows
    results = [r.strip() for r in raw if r.strip().startswith('r')]
    students: List[Student] = []

    # parse events
    events: Dict[datetime, List[Student]] = {}
    person = ''
    for r in results:
        # if a line with a name
        if '.name = ' in r:
            person: Student = Student(r[r.find('"') + 1:r.rfind('"')])
            students.append(person)
        # line with available times
        elif '.myCanDos = ' in r:
            # find the times
            available = r[r.find('"') + 1: r.find('"', r.find('"') + 1)]
            # convert to datetime and add to dict
            for a in available.split(','):
                a_dt = datetime.fromtimestamp(int(a) / 1000, timezone.utc)
                if a_dt in events:
                    events[a_dt].append(person)
                else:
                    events[a_dt] = [person]

    return students, Availability(events)


def find_schedules(schedule_so_far: Schedule, remaining_songs: List[Song],
                   all_schedules: List[Schedule], current_time: datetime, end_time: datetime):
    schedule_complete: bool = True

    for song in remaining_songs:
        if song.practice_length + current_time <= end_time:
            updated_schedule_so_far: Schedule = deepcopy(schedule_so_far)
            updated_schedule_so_far.song_order.append(song)

            updated_remaining_songs: List[Song] = deepcopy(remaining_songs)
            updated_remaining_songs.remove(song)
            current_time += song.practice_length

            find_schedules(updated_schedule_so_far, updated_remaining_songs, all_schedules,
                           current_time, end_time)
            current_time -= song.practice_length
            schedule_complete = False

    if schedule_complete:
        all_schedules.append(schedule_so_far)


def is_available(student: Student, start: datetime, end: datetime,
                 availability: Availability) -> bool:
    # Time should always be split up by half hour segments. This function doesnt work otherwise!
    if (start.minute != 0 and start.minute != 30) or (end.minute != 0 and end.minute != 30):
        print("wtf?")

    relevant_avails: List[List[Student]] = []
    print("asdfasdfas")
    print(availability.avails_dict)
    while start < end:
        print("start", start)

        if start in availability.avails_dict[start]:
            print("availability.avails_dict[start]", availability.avails_dict[start])
            relevant_avails.extend(availability.avails_dict[start])

        start += TIMESTEP

    print([avail for avail in relevant_avails])

    return all(student in avail for avail in relevant_avails)


def find_schedule_costs(all_schedules: List[Schedule], practice_start_time: datetime,
                        availability: Availability) -> None:
    for schedule in all_schedules:
        current_time: datetime = practice_start_time
        total_cost: float = 0

        for song in schedule.song_order:
            song_cost: float = 0
            start_song_time: datetime = current_time
            end_song_time: datetime = current_time + song.practice_length

            # Assign large cost if song leader can't be at practice
            if not is_available(song.leader, start_song_time, end_song_time, availability):
                song_cost += 50

            # Assign cost for each member that cant make it to practice
            for member in song.members:
                if not is_available(member, start_song_time, end_song_time, availability):
                    song_cost += 1

            # We square the song_cost because 1 song with 5 misses should be counted more heavily
            #  than 5 songs with 1 miss
            total_cost += pow(song_cost, 2)

        schedule.cost = total_cost


def main():
    # event and results codes as arguments
    event_id: str = "fyq9jbx"  # = sys.argv[1]
    response_code: str = "tm3bs28"  # = sys.argv[2]

    [students, availability] = get_whenisgood_availability(event_id, response_code)
    print(students)
    songs: List[Song] = [
        Song("Song 1", students[0], [students[1]]),
        Song("Song 2", students[1], [students[2]]),
        Song("Song 3", students[2], [students[3]]),
        Song("Song 4", students[3], [students[4]]),
    ]

    all_schedules: List[Schedule] = []
    schedule_so_far: Schedule = Schedule()
    remaining_songs: List[Song] = songs

    practice_start_time: datetime = datetime.fromtimestamp(1554141600, timezone.utc)   # datetime(2019, 4, 1, 18, tzinfo=timezone.utc)
    practice_end_time: datetime = datetime.fromtimestamp(1554163200, timezone.utc)     # datetime(2019, 4, 2, 0, tzinfo=timezone.utc)
    print(practice_start_time)
    print(practice_end_time)


    find_schedules(
        schedule_so_far, remaining_songs, all_schedules, practice_start_time, practice_end_time)
    find_schedule_costs(all_schedules, practice_start_time, availability)

    sorted_schedules = sorted(all_schedules, key=lambda s: s.cost)
    for schedule in sorted_schedules:
        print("schedule: ", schedule, "cost: ", schedule.cost)


if __name__ == "__main__":
    main()
