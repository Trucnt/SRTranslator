import os
import time
import logging
import timeit
import pickle

from typing import Optional, List

from selenium.webdriver import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.proxy import Proxy
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from .base import Translator, TimeOutException
from .selenium_utils import (
    create_proxy,
    create_driver,
)
from .selenium_components import (
    TextArea,
    Button,
    Text, BaseElement,
)

logger = logging.getLogger(__name__)

class DeeplTranslator(Translator):
    url = "https://www.deepl.com/translator"
    max_char = 3000
    proxy_address:List[str] = None
    languages = {
        "auto": "Any language (detect)",
        "bg": "Bulgarian",
        "zh": "Chinese",
        "cs": "Czech",
        "da": "Danish",
        "nl": "Dutch",
        "en": "English",  # Only usable for source language
        "en-US": "English (American)",  # Only usable for destination language
        "en-GB": "English (British)",  # Only usable for destination language
        "et": "Estonian",
        "fi": "Finnish",
        "fr": "French",
        "de": "German",
        "el": "Greek",
        "hu": "Hungarian",
        "id": "Indonesian",
        "it": "Italian",
        "ja": "Japanese",
        "ko": "Korean",
        "lv": "Latvian",
        "lt": "Lithuanian",
        "pl": "Polish",
        "pt": "Portuguese",  # Only usable for source language
        "pt-PT": "Portuguese",  # Only usable for destination language
        "pt-BR": "Portuguese (Brazilian)",  # Only usable for destination language
        "ro": "Romanian",
        "ru": "Russian",
        "sk": "Slovak",
        "sl": "Slovenian",
        "es": "Spanish",
        "sv": "Swedish",
        "tr": "Turkish",
        "uk": "Ukrainian",
    }

    def __init__(self, driver: Optional[WebDriver] = None, username: str = None, password: str = None):
        self.username = username
        self.password = password
        self.last_translation_failed = False  # last_translation_failed is False still stop drive and retry proxy new, try proxy still failed is True
        self.driver = driver

        if self.driver is None:
            self._rotate_proxy()
            return

        self._reset()

    def _reset(self):
        logger.info(f"Going to {self.url}")
        self.driver.get(self.url)
        #
        if os.getenv("LOGIN_AUTO"):
            try:
                self._set_login(self.username, self.password)
            except Exception as e:
                logger.exception(f"Error exception login :: error ", e)

        self._closePopUp()

        self.input_lang_from = TextArea(
            self.driver, "XPATH",f"//d-textarea[@data-testid='translator-source-input']" # @data-testid='translator-source-input'  @aria-labelledby='translation-source-heading'
        )
        self.input_destination_language = TextArea(
            self.driver, "XPATH",f"//d-textarea[@data-testid='translator-target-input']"
        )

        self.src_lang = None
        self.target_lang = None

    def _rotate_proxy(self):
        if self.driver is not None:
            logger.warning(" ======= Translation failed. Probably got banned. ======= ")
            logger.info("Rotating proxy")
            self.quit()

        proxy = create_proxy(proxyAddresses=self.proxy_address)
        self.driver = create_driver(proxy)
        self._reset()

    def _closePopUp(self):
        Button(
            self.driver,
            "CSS_SELECTOR",
            "[aria-label=Close]",
            #wait_time=50,
            optional=True,
        ).click()

    def _set_source_language(self, language: str) -> None:
        self._set_language(language, "//button[@data-testid='translator-source-lang-btn']")
        self.src_lang = language

    def _set_destination_language(self, language: str) -> None:
        self._set_language(language, "//button[@data-testid='translator-target-lang-btn']")
        self.target_lang = language

    def _set_language(self, language: str, dropdown_class: str) -> None:
        # Click the languages dropdown button
        Button(self.driver, "XPATH", dropdown_class).click()

        # Get the language button to click based on is dl-test property or the text in the button
        xpath_by_property = (
            f"//button[@data-testid='translator-lang-option-{language}']"
        )
        x_path_by_text = f"//button[text()='{self.languages[language]}']"
        xpath = f"{xpath_by_property} | {x_path_by_text}"

        # Click the wanted language button
        Button(self.driver, "XPATH", xpath).click()


    def _set_login(self, username: str, password: str) -> None:
        time.sleep(8)
        logger.info("Checking login username.")
        user_logged = None
        try:
            #find_element = self.driver.find_elements if multiple else self.driver.find_element
            #self.element = find_element((By.XPATH, f"//div[@class='dl_header_menu_v2__buttons__emailName_container']"))
            user_logged = Button(self.driver, "XPATH", f"//button[@data-testid='menu-account-in-btn']", optional=True)
            if user_logged and user_logged.element:
                self.username_current = user_logged.element.text
            else:
                self.username_current = None
        except:
            logger.info("Checking login failed.")
            self.username_current = None
        logger.info(f"Username current login :: {self.username_current}")
        if self.username_current is not None and ( len(self.username_current) > 0 > self.username_current.find(username)): # login others
            logger.info(f"Username existed user current logged {self.username_current}, need logout that.")
            user_logged.click() # Button(self.driver, "XPATH", f"//button[@data-testid='menu-account-in-btn']").click()
            time.sleep(3)
            Button(self.driver, "XPATH", f"//button[@data-testid='menu-account-logout']").click()
            # self.driver.execute_script('$(`[data-testid="menu-account-logout"]`).click()')
            time.sleep(6)
            self._closePopUp()
        elif self.username_current is not None and (len(self.username_current) > 0 and self.username_current.find(username) >= 0): # login same
            return

        button_login = Button(self.driver, "XPATH", f"//button[@data-testid='menu-account-out-btn']")
        button_login.click()
        time.sleep(4)
        input_email = TextArea(self.driver, "XPATH", f"//input[@data-testid='menu-login-username']")
        input_email.write(username)
        input_password = TextArea(self.driver, "XPATH", f"//input[@data-testid='menu-login-password']")
        input_password.write(password)
        logger.info("Enter login submit!")
        button_submit = Button(self.driver, "XPATH", f"//button[@data-testid='menu-login-submit']")
        button_submit.click()
        time.sleep(5)
        #
        notification = BaseElement(self.driver, "XPATH", f"//div[@data-testid='error-notification']", optional=True)
        if notification.element:
            logger.error(f"Check login status :: {notification.element.text}")
            logger.error(f"==========================================================================================")
        else:
            time.sleep(8)
            try:
                user_logged = Button(self.driver, "XPATH", f"//button[@data-testid='menu-account-in-btn']", optional=True)
                if user_logged and user_logged.element:
                    self.username_current = user_logged.element.text
                else:
                    self.username_current = None
            except:
                self.username_current = None

            logger.info(f"Now login with username :: {self.username_current}")

    def _is_translated(self, original: str, translation: str) -> bool:
        if (
                len(translation) != 0
                and len(original.splitlines()) == len(translation.splitlines())
                and original != translation
        ):
            return True
        else:
            logger.info(
                f"not _is_translated splitlines {len(original.splitlines()) == len(translation.splitlines())}   {len(original.splitlines())} {len(translation.splitlines())}")
            return False

    def translate(self, text: str, source_language: str, destination_language: str):
        try:
            start = timeit.default_timer()
            if source_language != self.src_lang:
                self._set_source_language(source_language)
            if destination_language != self.target_lang:
                self._set_destination_language(destination_language)

            if logger.isEnabledFor(logging.NOTSET): # https://stackoverflow.com/questions/42900214/how-to-download-a-html-webpage-using-selenium-with-python
                self.driver.save_screenshot(f"{self.src_lang}_{self.target_lang}_{start}.png")
                with open(f"{self.src_lang}_{self.target_lang}_{start}.html", "w", encoding='utf-8') as f:
                    f.write(self.driver.page_source)
            self.input_lang_from.write(value=(text), is_clipboard=True)
            logger.debug(f"TIME SET source {timeit.default_timer() - start}")
        except Exception as e:
            logger.warning("Error catch exception element.........................................................", e)

        try:
            time.sleep(4)
            for j in range(10):
                progress = BaseElement(self.driver,"XPATH", f"//*[@id='translator-progress-description']", optional=True)
                if logger.isEnabledFor(logging.NOTSET):
                    self.driver.save_screenshot(f"{self.src_lang}_{self.target_lang}_{start}___progress_{j}.png")
                    with open(f"{self.src_lang}_{self.target_lang}_{start}____progress_{j}.html", "w", encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                time.sleep(1)
                if progress and progress.element:
                    time.sleep(2)
                    print("*")
                if progress is None:
                    break
        except:
            pass

        if logger.isEnabledFor(logging.NOTSET):
            self.driver.save_screenshot(f"{self.src_lang}_{self.target_lang}_{start}_after_waiting.png")
            with open(f"{self.src_lang}_{self.target_lang}_{start}_after_waiting.html", "w", encoding='utf-8') as f:
                f.write(self.driver.page_source)
        # Maximun number of iterations 60 seconds
        for _ in range(10):
            try:
                translation = self.input_destination_language.value
                print(f"{start} :: translation output :: {_} :: {timeit.default_timer() - start}")

                if self._is_translated(text, translation):
                    # Reset the proxy flag -- is success - last not failed
                    self.last_translation_failed = False
                    try:
                        time.sleep(2)
                        self.driver.find_element(By.TAG_NAME,'body').send_keys(Keys.CONTROL + Keys.HOME)
                    except:
                        logger.info("Exception throw scroll by HOME")
                    return translation

                time.sleep(2)
            except Exception as e:
                logger.warning("Error catch exception.............................................................", e)

        # Maybe proxy got banned, so we try with a new proxy, but just once.
        if not self.last_translation_failed:  # failing, see_ing default is failing but first time not failed
            self.last_translation_failed = True
            self._rotate_proxy()
            return self.translate(text, source_language, destination_language)

        self.quit()
        raise TimeOutException("Translation timed out - Had try proxy but still failed.")

    def quit(self):
        self.driver.quit()
