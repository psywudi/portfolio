document.addEventListener('click', (event) => {
  const menu = document.querySelector('.work-menu');
  if (menu && !menu.contains(event.target)) menu.open = false;
});

const lightbox = document.getElementById('lightbox');
if (lightbox) {
  const expanded = lightbox.querySelector('img');
  document.querySelectorAll('.image-button').forEach((button) => {
    button.addEventListener('click', () => {
      const image = button.querySelector('img');
      expanded.src = image.src;
      expanded.alt = image.alt;
      lightbox.showModal();
    });
  });
  lightbox.querySelector('.close-lightbox').addEventListener('click', () => lightbox.close());
  lightbox.addEventListener('click', (event) => {
    if (event.target === lightbox) lightbox.close();
  });
  lightbox.addEventListener('close', () => {
    expanded.removeAttribute('src');
  });
}
