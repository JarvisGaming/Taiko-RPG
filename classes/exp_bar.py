class ExpBar:
    """Class representing an exp bar. Meant to be used in a dictionary as a value."""
    
    total_exp: int
    level: int
    exp_progress_to_next_level: int
    exp_required_for_next_level: int
    
    def __init__(self, total_exp: int):
        self.total_exp = total_exp
        self.__update_bar_based_on_total_exp()
    
    def add_exp(self, amount_of_exp_added: int):
        self.total_exp += amount_of_exp_added
        self.__update_bar_based_on_total_exp()
    
    def __update_bar_based_on_total_exp(self):
        current_exp = self.total_exp
        current_level = 1
        exp_required_for_next_level = 50
        
        # From the total exp in the bar, deduct the exp required for each subsequent level
        # Starting at level 1, reaching level 2 requires 50 exp, level 3 requires 100 more exp (so 150 exp total), etc
        while current_exp >= exp_required_for_next_level:
            current_level += 1
            current_exp -= exp_required_for_next_level
            exp_required_for_next_level += 50
        
        exp_progress_to_next_level = current_exp
        
        self.level = current_level
        self.exp_progress_to_next_level = exp_progress_to_next_level
        self.exp_required_for_next_level = exp_required_for_next_level